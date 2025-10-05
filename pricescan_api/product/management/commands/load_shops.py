import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from product.models import Shop

CHOICES = {"playwright", "beautifulsoup"}


def to_bool(v: str) -> bool:
    return str(v).strip().lower() in {"1", "true", "yes", "y", "да"}


def to_int(v):
    v = (v or "").strip()
    return int(v) if v.isdigit() else None


class Command(BaseCommand):
    help = "Импорт магазинов из CSV (id,name,domain,parser_type,is_active)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file", default="product/data/shop.csv", help="Путь к CSV файлу"
        )

    def handle(self, *args, **opts):
        path = Path(opts["file"])
        if not path.exists():
            self.stderr.write(self.style.ERROR(f"Файл не найден: {path}"))
            return

        created = updated = skipped = 0
        with path.open(encoding="utf-8") as f, transaction.atomic():
            reader = csv.DictReader(f)
            required = {"id", "name", "domain", "parser_type", "is_active"}
            if not required.issubset(set(reader.fieldnames or [])):
                self.stderr.write(
                    self.style.ERROR(
                        "Ожидаются столбцы: id,name,domain,parser_type,is_active"
                    )
                )
                return

            for row in reader:
                name = (row.get("name") or "").strip()
                domain = (row.get("domain") or "").strip()
                parser_type = (row.get("parser_type") or "").strip()
                is_active = to_bool(row.get("is_active"))

                if not name or not domain or parser_type not in CHOICES:
                    skipped += 1
                    continue

                pk = to_int(row.get("id"))
                defaults = {
                    "name": name,
                    "domain": domain,
                    "parser_type": parser_type,
                    "is_active": is_active,
                }

                if pk:
                    obj, is_created = Shop.objects.update_or_create(
                        pk=pk, defaults=defaults
                    )
                else:
                    obj, is_created = Shop.objects.update_or_create(
                        name=name, defaults=defaults
                    )

                if is_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Магазины: создано {created}, обновлено {updated}, пропущено {skipped}"
            )
        )
