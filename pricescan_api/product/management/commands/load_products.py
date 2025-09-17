import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from unidecode import unidecode

from product.models import Author, Category, Product, Publisher


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
    help = "Импорт продуктов из CSV (id,title,author,publisher,category,ean,brand,slug,description,image_url,min_players,max_players,playtime_min,min_age,external_id). Слаг игнорируется и генерируется заново."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default="product/data/products.csv",
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
                "author",
                "publisher",
                "category",
                "ean",
                "brand",
                "description",
                "image_url",
                "min_players",
                "max_players",
                "playtime_min",
                "min_age",
                "external_id",
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

                # FK
                author_id = to_int(row.get("author"))
                publisher_id = to_int(row.get("publisher"))
                category_id = to_int(row.get("category"))

                try:
                    author = Author.objects.get(pk=author_id) if author_id else None
                    publisher = (
                        Publisher.objects.get(pk=publisher_id) if publisher_id else None
                    )
                    category = (
                        Category.objects.get(pk=category_id) if category_id else None
                    )
                except (
                    Author.DoesNotExist,
                    Publisher.DoesNotExist,
                    Category.DoesNotExist,
                ):
                    if opts["strict-fk"]:
                        raise
                    skipped += 1
                    continue

                # Поля
                ean = (row.get("ean") or "").strip() or None
                brand = (row.get("brand") or "").strip() or None
                description = (row.get("description") or "").strip()
                image_url = (row.get("image_url") or "").strip() or None
                min_players = to_int(row.get("min_players"))
                max_players = to_int(row.get("max_players"))
                playtime_min = to_int(row.get("playtime_min"))
                min_age = to_int(row.get("min_age"))
                external_id = (row.get("external_id") or "").strip() or None

                # Слаг — генерируем заново (игнорируем CSV slug)
                base_slug = slugify(unidecode(title))
                slug = ensure_unique_slug(base_slug)

                pk = to_int(row.get("id"))
                defaults = {
                    "title": title,
                    "author": author,
                    "publisher": publisher,
                    "category": category,
                    "ean": ean,
                    "brand": brand,
                    "slug": slug,
                    "description": description,
                    "image_url": image_url,
                    "min_players": min_players,
                    "max_players": max_players,
                    "playtime_min": playtime_min,
                    "min_age": min_age,
                    "external_id": external_id,
                }

                if pk:
                    obj, is_created = Product.objects.update_or_create(
                        pk=pk, defaults=defaults
                    )
                else:
                    # если id не задан — пробуем по ean или external_id
                    lookup = {}
                    if ean:
                        lookup["ean"] = ean
                    elif external_id:
                        lookup["external_id"] = external_id
                    obj, is_created = (
                        Product.objects.update_or_create(defaults=defaults, **lookup)
                        if lookup
                        else Product.objects.get_or_create(
                            title=title, defaults=defaults
                        )
                    )

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
