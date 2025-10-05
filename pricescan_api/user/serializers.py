from django.contrib.auth import get_user_model
from rest_framework import serializers

from product.models import Offer

from .models import UserFavorite

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "uuid",
            "email",
            "first_name",
            "last_name",
            "telegram_id",
            "telegram_username",
            "language_code",
        )
        read_only_fields = ("uuid", "telegram_id")


class BotAuthRequestSerializer(serializers.Serializer):
    telegram_id = serializers.IntegerField()
    telegram_username = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    language_code = serializers.CharField(
        required=False, allow_blank=True, max_length=8
    )

    def validate_first_name(self, v):
        return (v or "").strip()

    def validate_last_name(self, v):
        return (v or "").strip()

    def validate_language_code(self, v):
        return v or None


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class UserFavoriteSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source="product.title", read_only=True)
    first_offer_url = serializers.SerializerMethodField()

    def get_first_offer_url(self, obj):
        offer = (
            Offer.objects.filter(product=obj.product, is_available=True)
            .order_by("price")
            .first()
        )
        return offer.url if offer else None

    class Meta:
        model = UserFavorite
        fields = ("id", "product", "product_title", "first_offer_url", "added_at")
        read_only_fields = ("id", "added_at")


# class SearchHistorySerializer(serializers.ModelSerializer):
#     class Meta:
#         model = SearchHistory
#         fields = ("id", "query", "search_date", "results_count")
#         read_only_fields = ("id", "search_date")
