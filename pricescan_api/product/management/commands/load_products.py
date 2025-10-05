import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from unidecode import unidecode

from product.models import Category, Product, Publisher


def to_int(v):
    v = (v or "").strip()
    return int(v) if v.isdigit() else None


def ensure_unique_slug(base: str) -> str:
    slug = base or "item"
    i = 2
    while Product.objects.filter(slug=slug).exists():
        slug = f"{base}-{i}"
        i += 1
    return slug


class Command(BaseCommand):
    help = "Импорт продуктов из CSV (id,title,publisher,category,slug,min_players,max_players,playtime_min,min_age,external_id). Слаг игнорируется и генерируется заново."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default="product/data/product.csv",
            help="Путь к CSV файлу с продуктами",
        )
        parser.add_argument(
            "--strict-fk",
            action="store_true",
            help="Падать с ошибкой, если не найден author/publisher/category по id",
        )

    def handle(self, *args, **opts):
        path = Path(opts["file"])
        if not path.exists():
            self.stderr.write(self.style.ERROR(f"Файл не найден: {path}"))
            return

        created = updated = skipped = 0
        with path.open(encoding="utf-8") as f, transaction.atomic():
            reader = csv.DictReader(f)
            required = {
                "id",
                "title",
                "publishers",
                "categories", 
                "min_players",
                "max_players",
                "playtime_min",
                "min_age",
            }
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise ValueError(
                    f"В CSV отсутствуют столбцы: {', '.join(sorted(missing))}"
                )

            for row in reader:
                title = (row.get("title") or "").strip()
                if not title:
                    skipped += 1
                    continue

                # Обрабатываем publishers (список ID через запятую)
                publishers = []
                publishers_str = row.get("publishers", "").strip()
                if publishers_str:
                    for pub_id in publishers_str.split(","):
                        pub_id = pub_id.strip()
                        if pub_id.isdigit():
                            try:
                                pub = Publisher.objects.get(pk=int(pub_id))
                                publishers.append(pub)
                            except Publisher.DoesNotExist:
                                if opts["strict-fk"]:
                                    raise
                                continue

                # Обрабатываем categories (список ID через запятую)
                categories = []
                categories_str = row.get("categories", "").strip()
                if categories_str:
                    for cat_id in categories_str.split(","):
                        cat_id = cat_id.strip()
                        if cat_id.isdigit():
                            try:
                                cat = Category.objects.get(pk=int(cat_id))
                                categories.append(cat)
                            except Category.DoesNotExist:
                                if opts["strict-fk"]:
                                    raise
                                continue

                # Поля
                min_players = to_int(row.get("min_players"))
                max_players = to_int(row.get("max_players"))
                playtime_min = to_int(row.get("playtime_min"))
                min_age = to_int(row.get("min_age"))

                # Слаг — генерируем заново
                base_slug = slugify(unidecode(title))
                slug = ensure_unique_slug(base_slug)

                pk = to_int(row.get("id"))
                defaults = {
                    "title": title,
                    "slug": slug,
                    "min_players": min_players,
                    "max_players": max_players,
                    "playtime_min": playtime_min,
                    "min_age": min_age,
                }

                if pk:
                    obj, is_created = Product.objects.update_or_create(
                        pk=pk, defaults=defaults
                    )
                else:
                    obj, is_created = Product.objects.get_or_create(
                        title=title, defaults=defaults
                    )

                # Устанавливаем ManyToMany связи ПОСЛЕ создания объекта
                if publishers:
                    obj.publishers.set(publishers)
                if categories:
                    obj.categories.set(categories)

                # гарантируем уникальный slug для уже существующих
                if Product.objects.exclude(pk=obj.pk).filter(slug=obj.slug).exists():
                    obj.slug = ensure_unique_slug(base_slug)
                    obj.save(update_fields=["slug"])

                if is_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Готово. Создано: {created}, обновлено: {updated}, пропущено: {skipped}"
            )
        )
