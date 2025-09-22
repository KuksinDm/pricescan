from rest_framework import serializers

from .models import Alert, AlertHistory, AlertType


class AlertSerializer(serializers.ModelSerializer):
    """Сериализатор для алертов"""

    product_title = serializers.CharField(source="product.title", read_only=True)
    product_author = serializers.CharField(source="product.author.name", read_only=True)
    shop_name = serializers.CharField(source="shop.name", read_only=True)
    alert_type_display = serializers.CharField(
        source="get_alert_type_display", read_only=True
    )

    class Meta:
        model = Alert
        fields = [
            "id",
            "product",
            "product_title",
            "product_author",
            "shop",
            "shop_name",
            "alert_type",
            "alert_type_display",
            "threshold_price",
            "currency",
            "is_active",
            "is_triggered",
            "last_triggered_at",
            "trigger_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "is_triggered",
            "last_triggered_at",
            "trigger_count",
            "created_at",
            "updated_at",
        ]


class AlertCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания алертов"""

    class Meta:
        model = Alert
        fields = ["product", "shop", "alert_type", "threshold_price", "currency"]

    def validate_threshold_price(self, value):
        """Валидация пороговой цены"""
        if value <= 0:
            raise serializers.ValidationError("Пороговая цена должна быть больше 0")
        return value

    def validate_alert_type(self, value):
        """Валидация типа алерта"""
        if value not in [choice[0] for choice in AlertType.choices]:
            raise serializers.ValidationError("Недопустимый тип алерта")
        return value


class AlertHistorySerializer(serializers.ModelSerializer):
    """Сериализатор для истории алертов"""

    shop_name = serializers.CharField(source="shop.name", read_only=True)
    alert_product_title = serializers.CharField(
        source="alert.product.title", read_only=True
    )

    class Meta:
        model = AlertHistory
        fields = [
            "id",
            "alert",
            "alert_product_title",
            "triggered_at",
            "old_price",
            "new_price",
            "currency",
            "shop",
            "shop_name",
            "message",
        ]
        read_only_fields = ["id", "triggered_at"]


class AlertStatisticsSerializer(serializers.Serializer):
    """Сериализатор для статистики алертов"""

    total_alerts = serializers.IntegerField()
    active_alerts = serializers.IntegerField()
    triggered_alerts = serializers.IntegerField()
    alerts_by_type = serializers.DictField()
