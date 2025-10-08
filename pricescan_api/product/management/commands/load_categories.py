import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from unidecode import unidecode

from product.models import Category


def make_unique_slug(base_slug: str) -> str:
    slug = base_slug
    i = 2
    while Category.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{i}"
        i += 1
    return slug


class Command(BaseCommand):
    help = "Импорт категорий из CSV (столбцы: id,name). Генерирует английские слаги."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=str(Path("product") / "data" / "category.csv"),
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
                    result = self._process_category_row(row, options)
                    if result == "created":
                        created += 1
                    elif result == "updated":
                        updated += 1
                    else:
                        skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Готово. Создано: {created}, обновлено: "
                f"{updated}, пропущено: {skipped}"
            )
        )

    def _process_category_row(self, row, options):
        name = (row.get("name") or "").strip()
        if not name:
            return "skipped"

        base_slug = slugify(unidecode(name))
        if not base_slug:
            return "skipped"

        pk = (row.get("id") or "").strip()
        if pk.isdigit():
            obj, is_created = Category.objects.update_or_create(
                pk=int(pk),
                defaults={"name": name, "slug": base_slug},
            )
        else:
            obj, is_created = Category.objects.get_or_create(name=name)
            self._update_slug_if_needed(obj, base_slug, is_created)

        self._ensure_unique_slug(obj, base_slug, options)

        if options["dry_run"]:
            return "skipped"

        return "created" if is_created else "updated"

    def _update_slug_if_needed(self, obj, desired_slug, is_created):
        if not obj.slug or obj.slug != desired_slug:
            obj.slug = desired_slug
            obj.save(update_fields=["slug"])

    def _ensure_unique_slug(self, obj, base_slug, options):
        if Category.objects.exclude(pk=obj.pk).filter(slug=obj.slug).exists():
            obj.slug = make_unique_slug(base_slug)
            if not options["dry_run"]:
                obj.save(update_fields=["slug"])
