import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from unidecode import unidecode

from product.models import Author


def make_unique_slug(base_slug: str) -> str:
    slug = base_slug
    i = 2
    while Author.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{i}"
        i += 1
    return slug


class Command(BaseCommand):
    help = "Импорт авторов из CSV (столбцы: id,name). Генерирует английские слаги."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=str(Path("product") / "data" / "authors.csv"),
            help="Путь к CSV файлу",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Показать, что будет сделано, без сохранения",
        )

    def handle(self, *args, **options):
        path = Path(options["file"])
        if not path.exists():
            self.stderr.write(self.style.ERROR(f"Файл не найден: {path}"))
            return

        created = updated = skipped = 0

        with path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if "name" not in reader.fieldnames:
                self.stderr.write(self.style.ERROR("В CSV должен быть столбец 'name'"))
                return

            with transaction.atomic():
                for row in reader:
                    name = (row.get("name") or "").strip()
                    if not name:
                        skipped += 1
                        continue

                    base_slug = slugify(unidecode(name))
                    if not base_slug:
                        skipped += 1
                        continue

                    pk = (row.get("id") or "").strip()
                    if pk.isdigit():
                        obj, is_created = Author.objects.update_or_create(
                            pk=int(pk),
                            defaults={"name": name, "slug": base_slug},
                        )
                    else:
                        obj, is_created = Author.objects.get_or_create(name=name)
                        # проставим/обновим slug
                        desired = base_slug
                        if not obj.slug or obj.slug != desired:
                            obj.slug = desired
                            is_created = is_created  # не меняем флаг
                            obj.save(update_fields=["slug"])

                    # обеспечим уникальность slug (с суффиксом -2, -3...)
                    if Author.objects.exclude(pk=obj.pk).filter(slug=obj.slug).exists():
                        obj.slug = make_unique_slug(base_slug)
                        if not options["dry_run"]:
                            obj.save(update_fields=["slug"])

                    if options["dry_run"]:
                        skipped += 1
                        continue

                    if is_created:
                        created += 1
                    else:
                        updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Готово. Создано: {created}, обновлено: {updated}, пропущено: {skipped}"
            )
        )
