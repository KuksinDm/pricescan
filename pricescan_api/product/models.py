from django.conf import settings
from django.db import models
from django.utils.text import slugify
from unidecode import unidecode


class Category(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(unidecode(self.name))
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"


class Author(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(unidecode(self.name))
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Publisher(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(unidecode(self.name))
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Издатель"
        verbose_name_plural = "Издатели"


class Product(models.Model):
    # Основная информация о книге
    title = models.CharField(max_length=500)
    slug = models.SlugField(max_length=200, unique=True)
    # Множественные связи
    authors = models.ManyToManyField(Author, related_name="products", blank=True)
    publishers = models.ManyToManyField(Publisher, related_name="products", blank=True)
    categories = models.ManyToManyField(Category, related_name="products", blank=True)

    # Игровые характеристики
    min_players = models.PositiveIntegerField(null=True, blank=True)
    max_players = models.PositiveIntegerField(null=True, blank=True)
    playtime_min = models.PositiveIntegerField(null=True, blank=True)
    min_age = models.PositiveIntegerField(null=True, blank=True)

    # Системные поля
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["title"]),
        ]
        verbose_name = "Игра"
        verbose_name_plural = "Игры"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(unidecode(self.title))
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Shop(models.Model):
    name = models.CharField(max_length=100)
    domain = models.URLField()
    parser_type = models.CharField(
        max_length=20,
        choices=[
            ("playwright", "Playwright"),
            ("beautifulsoup", "BeautifulSoup"),
        ],
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Магазин"
        verbose_name_plural = "Магазины"


class Offer(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="offers"
    )
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)

    # Цена и наличие
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="RUB")
    is_available = models.BooleanField(default=True)

    # Ссылка и метаданные
    url = models.URLField()
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["product", "shop"]
        indexes = [
            models.Index(fields=["price"]),
            models.Index(fields=["last_updated"]),
        ]
        verbose_name = "Предложение"
        verbose_name_plural = "Предложения"

    def __str__(self):
        return f"{self.product} @ {self.shop}"


class PriceHistory(models.Model):
    offer = models.ForeignKey(
        Offer, on_delete=models.CASCADE, related_name="price_history"
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="RUB")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["timestamp"]),
        ]
        verbose_name = "История цен"
        verbose_name_plural = "История цен"

    def __str__(self):
        return f"{self.price} {self.currency}"


class PriceAlert(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="price_alerts"
    )
    product = models.ForeignKey(
        "product.Product", on_delete=models.CASCADE, related_name="price_alerts"
    )
    shop = models.ForeignKey(
        "product.Shop", on_delete=models.CASCADE, null=True, blank=True
    )  # опционально: алерт по конкретному магазину
    threshold_price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="RUB")
    is_active = models.BooleanField(default=True)
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "product", "shop", "threshold_price", "currency")
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["product", "is_active"]),
            models.Index(fields=["threshold_price"]),
        ]
        verbose_name = "Алерт"
        verbose_name_plural = "Алерты"

    def __str__(self):
        return f"{self.product.title} - {self.threshold_price} {self.currency}"
