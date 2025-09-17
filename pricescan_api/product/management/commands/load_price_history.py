import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import get_default_timezone, make_aware

from product.models import Offer, PriceHistory


def to_decimal(v):
    try:
        return Decimal(str(v).replace(",", "."))
    except (InvalidOperation, TypeError):
        return None


class Command(BaseCommand):
    help = "Импорт истории цен из CSV (id,offer,price,ts). Дата ts в формате 'YYYY-MM-DD HH:MM:SS'."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file", default="product/data/price_history.csv", help="Путь к CSV файлу"
        )
        parser.add_argument(
            "--truncate", action="store_true", help="Очистить историю перед импортом"
        )

    def handle(self, *args, **opts):
        path = Path(opts["file"])
        if not path.exists():
            self.stderr.write(self.style.ERROR(f"Файл не найден: {path}"))
            return

        if opts["truncate"]:
            PriceHistory.objects.all().delete()
            self.stdout.write(self.style.WARNING("Таблица PriceHistory очищена."))

        created = skipped = 0
        tz = get_default_timezone()

        with path.open(encoding="utf-8") as f, transaction.atomic():
            reader = csv.DictReader(f)
            required = {"id", "offer", "price", "ts"}
            if not required.issubset(set(reader.fieldnames or [])):
                self.stderr.write(
                    self.style.ERROR(
                        f"Ожидаются столбцы: {', '.join(sorted(required))}"
                    )
                )
                return

            for row in reader:
                offer_id = (row.get("offer") or "").strip()
                price = to_decimal(row.get("price"))
                ts_raw = (row.get("ts") or "").strip()
                if not offer_id or price is None or not ts_raw:
                    skipped += 1
                    continue

                try:
                    offer = Offer.objects.get(pk=int(offer_id))
                except (ValueError, Offer.DoesNotExist):
                    skipped += 1
                    continue

                try:
                    dt = datetime.strptime(ts_raw, "%Y-%m-%d %H:%M:%S")
                    ts = make_aware(dt, tz)
                except ValueError:
                    skipped += 1
                    continue

                # валюту берём из оффера, если нужно
                PriceHistory.objects.create(
                    offer=offer, price=price, currency=offer.currency, timestamp=ts
                )
                created += 1

        self.stdout.write(
            self.style.SUCCESS(f"История цен: создано {created}, пропущено {skipped}")
        )
