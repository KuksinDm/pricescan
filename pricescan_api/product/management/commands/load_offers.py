# product/management/commands/load_offers.py
import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from product.models import Offer, PriceHistory, Product, Shop


def to_int(v):
    v = (v or "").strip()
    return int(v) if v.isdigit() else None


def to_bool(v) -> bool:
    return str(v).strip().lower() in {"1", "true", "yes", "y", "да"}


class Command(BaseCommand):
    help = (
        "Импорт офферов из CSV (id,product,shop,price,currency,is_available,url). "
        "Обновляет по (product, shop). Опционально пишет PriceHistory."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default="product/data/offer.csv",
            help="Путь к CSV файлу",
        )
        parser.add_argument(
            "--history",
            action="store_true",
            help="Создавать запись в PriceHistory при изменении цены",
        )

    def handle(self, *args, **opts):
        path = Path(opts["file"])
        if not path.exists():
            self.stderr.write(self.style.ERROR(f"Файл не найден: {path}"))
            return

        created = updated = skipped = history = 0

        with path.open(encoding="utf-8") as f, transaction.atomic():
            reader = csv.DictReader(f)
            required = {
                "id",
                "product",
                "shop",
                "price",
                "currency",
                "is_available",
                "url",
            }
            if not required.issubset(set(reader.fieldnames or [])):
                self.stderr.write(
                    self.style.ERROR(
                        f"Ожидаются столбцы: {', '.join(sorted(required))}"
                    )
                )
                return

            for row in reader:
                try:
                    product_id = to_int(row.get("product"))
                    shop_id = to_int(row.get("shop"))
                    if not product_id or not shop_id:
                        skipped += 1
                        continue

                    try:
                        product = Product.objects.get(pk=product_id)
                        shop = Shop.objects.get(pk=shop_id)
                    except (Product.DoesNotExist, Shop.DoesNotExist):
                        skipped += 1
                        continue

                    try:
                        price = Decimal(str(row.get("price", "")).replace(",", "."))
                    except (InvalidOperation, TypeError):
                        skipped += 1
                        continue

                    currency = (row.get("currency") or "RUB").strip().upper()[:3]
                    is_available = to_bool(row.get("is_available"))
                    url = (row.get("url") or "").strip()
                    if not url:
                        skipped += 1
                        continue

                    pk = to_int(row.get("id"))
                    defaults = {
                        "product": product,
                        "shop": shop,
                        "price": price,
                        "currency": currency,
                        "is_available": is_available,
                        "url": url,
                    }

                    # Если есть pk — обновляем по pk, иначе по уникальной паре (product, shop)
                    if pk:
                        obj, is_created = Offer.objects.update_or_create(
                            pk=pk, defaults=defaults
                        )
                    else:
                        # уникальность обеспечивается unique_together (product, shop)
                        obj, is_created = Offer.objects.update_or_create(
                            product=product, shop=shop, defaults=defaults
                        )

                    if is_created:
                        created += 1
                        if opts["history"]:
                            PriceHistory.objects.create(
                                offer=obj, price=price, currency=currency
                            )
                            history += 1
                    else:
                        # Если цена изменилась — пишем историю при флаге
                        old = Offer.objects.get(pk=obj.pk)
                        if opts["history"] and old.price != price:
                            PriceHistory.objects.create(
                                offer=obj, price=price, currency=currency
                            )
                            history += 1
                        updated += 1

                except Exception:
                    skipped += 1
                    # Можно раскомментировать для дебага:
                    # self.stderr.write(f"Skip row due to error: {e}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Офферы: создано {created}, обновлено {updated}, пропущено {skipped}, history={history}"
            )
        )
