from rest_framework import serializers

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


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ("id", "name", "slug")


class PublisherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publisher
        fields = ("id", "name", "slug")


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ("name",)


class OfferSerializer(serializers.ModelSerializer):
    shop = ShopSerializer(read_only=True)
    product_title = serializers.CharField(source="product.title", read_only=True)
    product_author = serializers.CharField(source="product.author.name", read_only=True)
    product_publisher = serializers.CharField(source="product.publisher.name", read_only=True)
    product_category = serializers.CharField(source="product.category.name", read_only=True)
    min_players = serializers.IntegerField(source="product.min_players", read_only=True)
    max_players = serializers.IntegerField(source="product.max_players", read_only=True)
    playtime_min = serializers.IntegerField(source="product.playtime_min", read_only=True)
    min_age = serializers.IntegerField(source="product.min_age", read_only=True)
    description = serializers.CharField(source="product.description", read_only=True)
    image_url = serializers.URLField(source="product.image_url", read_only=True)

    class Meta:
        model = Offer
        fields = (
            "id",
            "product",
            "product_title",
            "product_author",
            "product_publisher",
            "product_category",
            "min_players",
            "max_players",
            "playtime_min",
            "min_age",
            "description",
            "image_url",
            "price",
            "currency",
            "is_available",
            "shop",
            "url",
            "last_updated",
        )


class PriceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceHistory
        fields = ("id", "price", "currency", "timestamp")


class ProductSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    publisher = PublisherSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    min_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    offers_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "title",
            "slug",
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
            "min_price",
            "offers_count",
        )


class PriceAlertSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source="product.title", read_only=True)

    class Meta:
        model = PriceAlert
        fields = (
            "id",
            "product",
            "product_title",
            "shop",
            "threshold_price",
            "currency",
            "is_active",
            "last_triggered_at",
            "created_at",
        )
        read_only_fields = ("last_triggered_at", "created_at")
