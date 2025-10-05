from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from .models import (
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


class ProductCategoryInline(admin.TabularInline):
    model = Product.categories.through
    extra = 0
    autocomplete_fields = ("category",)


class ProductPublisherInline(admin.TabularInline):
    model = Product.publishers.through
    extra = 0
    autocomplete_fields = ("publisher",)


@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    list_display = (
        "id",
        "title",
        "get_publishers_display",
        "get_categories_display",
        "min_players",
        "max_players",
        "min_age",
        "created_at",
        "updated_at",
    )
    list_filter = (
        "categories",
        "publishers",
        "min_age",
        "created_at",
    )
    search_fields = ("title", "publishers__name", "categories__name")
    filter_horizontal = ("publishers", "categories")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [OfferInline]
    ordering = ("-updated_at",)
    readonly_fields = ("created_at", "updated_at")

    def get_publishers_display(self, obj):
        """Показывает всех издателей в списке"""
        return ", ".join([publisher.name for publisher in obj.publishers.all()[:3]])

    get_publishers_display.short_description = "Издатели"

    def get_categories_display(self, obj):
        """Показывает все категории в списке"""
        return ", ".join([category.name for category in obj.categories.all()[:3]])

    get_categories_display.short_description = "Категории"


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
    list_filter = ("shop", "currency", "is_available", "last_updated")
    search_fields = ("product__title", "shop__name")
    autocomplete_fields = ("product", "shop")
    inlines = [PriceHistoryInline]
    ordering = ("price",)
    readonly_fields = ("last_updated",)


@admin.register(PriceHistory)
class PriceHistoryAdmin(ImportExportModelAdmin):
    list_display = ("id", "offer", "price", "currency", "timestamp")
    list_filter = ("currency", "timestamp")
    search_fields = ("offer__product__title", "offer__shop__name")
    autocomplete_fields = ("offer",)
    ordering = ("-timestamp",)


@admin.register(Shop)
class ShopAdmin(ImportExportModelAdmin):
    list_display = ("id", "name", "domain", "parser_type", "is_active")
    list_filter = ("parser_type", "is_active")
    search_fields = ("name", "domain")


@admin.register(Category)
class CategoryAdmin(ImportExportModelAdmin):
    list_display = ("id", "name", "slug", "products_count")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)

    def products_count(self, obj):
        """Показывает количество продуктов в категории"""
        return obj.products.count()

    products_count.short_description = "Количество продуктов"


@admin.register(Publisher)
class PublisherAdmin(ImportExportModelAdmin):
    list_display = ("id", "name", "slug", "products_count")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)

    def products_count(self, obj):
        """Показывает количество продуктов издателя"""
        return obj.products.count()

    products_count.short_description = "Количество продуктов"


@admin.register(PriceAlert)
class PriceAlertAdmin(ImportExportModelAdmin):
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
    list_filter = ("is_active", "currency", "shop", "created_at")
    search_fields = ("user__username", "product__title", "shop__name")
    autocomplete_fields = ("user", "product", "shop")
    readonly_fields = ("last_triggered_at", "created_at")
