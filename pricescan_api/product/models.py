from django.conf import settings
from django.db import models
from django.utils.text import slugify
from unidecode import unidecode

from .constants import (
    CURRENCY_LENGTH,
    DEFAULT_CURRENCY,
    NAME_MAX_LENGTH,
    PARSER_TYPE_MAX_LENGTH,
    PRICE_DECIMAL_PLACES,
    PRICE_MAX_DIGITS,
    SHOP_NAME_MAX_LENGTH,
    SLUG_MAX_LENGTH,
    TITLE_MAX_LENGTH,
)


class Category(models.Model):
    name = models.CharField(max_length=NAME_MAX_LENGTH, unique=True)
    slug = models.SlugField(max_length=SLUG_MAX_LENGTH, unique=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(unidecode(self.name))
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"


class Publisher(models.Model):
    name = models.CharField(max_length=NAME_MAX_LENGTH)
    slug = models.SlugField(max_length=SLUG_MAX_LENGTH)

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
    title = models.CharField(max_length=TITLE_MAX_LENGTH)
    slug = models.SlugField(max_length=SLUG_MAX_LENGTH, unique=True)

    # Множественные связи
    publishers = models.ManyToManyField(Publisher, related_name="products", blank=True)
    categories = models.ManyToManyField(Category, related_name="products", blank=True)

    min_players = models.PositiveIntegerField(null=True, blank=True)
    max_players = models.PositiveIntegerField(null=True, blank=True)
    playtime_min = models.PositiveIntegerField(null=True, blank=True)
    min_age = models.PositiveIntegerField(null=True, blank=True)

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
    name = models.CharField(max_length=SHOP_NAME_MAX_LENGTH)
    domain = models.URLField()
    parser_type = models.CharField(
        max_length=PARSER_TYPE_MAX_LENGTH,
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
    price = models.DecimalField(
        max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES
    )
    currency = models.CharField(max_length=CURRENCY_LENGTH, default=DEFAULT_CURRENCY)
    is_available = models.BooleanField(default=True)
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
    price = models.DecimalField(
        max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES
    )
    currency = models.CharField(max_length=CURRENCY_LENGTH, default=DEFAULT_CURRENCY)
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
    )
    threshold_price = models.DecimalField(
        max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES
    )
    currency = models.CharField(max_length=CURRENCY_LENGTH, default=DEFAULT_CURRENCY)
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
