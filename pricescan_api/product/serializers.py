from rest_framework import serializers

from .models import (
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
    # ManyToMany поля - показываем всех авторов/издателей/категории
    product_publishers = serializers.SerializerMethodField()
    product_categories = serializers.SerializerMethodField()

    min_players = serializers.IntegerField(source="product.min_players", read_only=True)
    max_players = serializers.IntegerField(source="product.max_players", read_only=True)
    playtime_min = serializers.IntegerField(
        source="product.playtime_min", read_only=True
    )
    min_age = serializers.IntegerField(source="product.min_age", read_only=True)

    class Meta:
        model = Offer
        fields = (
            "id",
            "product",
            "product_title",
            "product_publishers",
            "product_categories",
            "min_players",
            "max_players",
            "playtime_min",
            "min_age",
            "price",
            "currency",
            "is_available",
            "shop",
            "url",
        )

    def get_product_publishers(self, obj):
        """Возвращает всех издателей"""
        return [publisher.name for publisher in obj.product.publishers.all()]

    def get_product_categories(self, obj):
        """Возвращает все категории"""
        return [category.name for category in obj.product.categories.all()]


class PriceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceHistory
        fields = ("id", "price", "currency", "timestamp")


class ProductSerializer(serializers.ModelSerializer):
    publishers = PublisherSerializer(many=True, read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
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
            "publishers",
            "categories",
            "min_players",
            "max_players",
            "playtime_min",
            "min_age",
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
        )
        read_only_fields = ("last_triggered_at",)
