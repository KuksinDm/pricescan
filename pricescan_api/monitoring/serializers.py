from rest_framework import serializers

from .models import (
    AlertRule,
    AlertTrigger,
    Metric,
    MetricValue,
    PerformanceLog,
    SystemHealth,
)


class MetricSerializer(serializers.ModelSerializer):
    """Сериализатор для метрик"""

    metric_type_display = serializers.CharField(
        source="get_metric_type_display", read_only=True
    )

    class Meta:
        model = Metric
        fields = [
            "id",
            "name",
            "metric_type",
            "metric_type_display",
            "description",
            "labels",
            "value",
            "last_updated",
            "is_active",
            "unit",
        ]
        read_only_fields = ["id", "last_updated"]


class MetricValueSerializer(serializers.ModelSerializer):
    """Сериализатор для значений метрик"""

    class Meta:
        model = MetricValue
        fields = ["id", "metric", "value", "labels", "timestamp"]
        read_only_fields = ["id", "timestamp"]


class SystemHealthSerializer(serializers.ModelSerializer):
    """Сериализатор для состояния системы"""

    class Meta:
        model = SystemHealth
        fields = [
            "id",
            "service_name",
            "is_healthy",
            "status_message",
            "last_check",
            "response_time_ms",
            "extra_data",
        ]
        read_only_fields = ["id", "last_check"]


class AlertRuleSerializer(serializers.ModelSerializer):
    """Сериализатор для правил алертов"""

    metric_name = serializers.CharField(source="metric.name", read_only=True)
    comparison_operator_display = serializers.CharField(
        source="get_comparison_operator_display", read_only=True
    )
    severity_display = serializers.CharField(
        source="get_severity_display", read_only=True
    )

    class Meta:
        model = AlertRule
        fields = [
            "id",
            "name",
            "metric",
            "metric_name",
            "threshold_value",
            "comparison_operator",
            "comparison_operator_display",
            "is_active",
            "severity",
            "severity_display",
            "notification_channels",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AlertTriggerSerializer(serializers.ModelSerializer):
    """Сериализатор для срабатываний алертов"""

    rule_name = serializers.CharField(source="rule.name", read_only=True)
    metric_name = serializers.CharField(source="rule.metric.name", read_only=True)

    class Meta:
        model = AlertTrigger
        fields = [
            "id",
            "rule",
            "rule_name",
            "metric_name",
            "triggered_at",
            "resolved_at",
            "is_resolved",
            "metric_value",
            "threshold_value",
            "message",
        ]
        read_only_fields = ["id", "triggered_at"]


class PerformanceLogSerializer(serializers.ModelSerializer):
    """Сериализатор для логов производительности"""

    class Meta:
        model = PerformanceLog
        fields = [
            "id",
            "endpoint",
            "method",
            "response_time_ms",
            "status_code",
            "user_id",
            "ip_address",
            "user_agent",
            "request_size_bytes",
            "response_size_bytes",
            "timestamp",
        ]
        read_only_fields = ["id", "timestamp"]


class SystemOverviewSerializer(serializers.Serializer):
    """Сериализатор для общего обзора системы"""

    services = serializers.DictField()
    metrics = serializers.DictField()
    performance = serializers.DictField()
    alerts = serializers.DictField()
