from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from .models import (
    Author,
    Category,
    Offer,
    PriceAlert,
    PriceHistory,
    Product,
    Publisher,
    Shop,
)


class OfferInline(admin.TabularInline):
    model = Offer
    extra = 0
    fields = ("shop", "price", "currency", "is_available", "url", "last_updated")
    readonly_fields = ("last_updated",)


class PriceHistoryInline(admin.TabularInline):
    model = PriceHistory
    extra = 0
    fields = ("price", "currency", "timestamp")
    readonly_fields = ("timestamp",)


@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    list_display = (
        "id",
        "title",
        "author",
        "publisher",
        "category",
        "ean",
        "brand",
        "min_players",
        "max_players",
        "min_age",
        "updated_at",
    )
    list_filter = ("category", "publisher", "min_age")
    search_fields = ("title", "ean", "brand", "author__name", "publisher__name")
    autocomplete_fields = ("author", "publisher", "category")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [OfferInline]
    ordering = ("-updated_at",)


@admin.register(Offer)
class OfferAdmin(ImportExportModelAdmin):
    list_display = (
        "id",
        "product",
        "shop",
        "price",
        "currency",
        "is_available",
        "last_updated",
    )
    list_filter = ("shop", "currency", "is_available")
    search_fields = ("product__title", "shop__name")
    autocomplete_fields = ("product", "shop")
    inlines = [PriceHistoryInline]
    ordering = ("price",)


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "offer", "price", "currency", "timestamp")
    list_filter = ("currency",)
    search_fields = ("offer__product__title", "offer__shop__name")
    autocomplete_fields = ("offer",)
    ordering = ("-timestamp",)


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "domain", "parser_type", "is_active")
    list_filter = ("parser_type", "is_active")
    search_fields = ("name", "domain")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(PriceAlert)
class PriceAlertAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "product",
        "shop",
        "threshold_price",
        "currency",
        "is_active",
        "last_triggered_at",
        "created_at",
    )
    list_filter = ("is_active", "currency", "shop")
    search_fields = ("user__username", "product__title", "shop__name")
    autocomplete_fields = ("user", "product", "shop")
