from django.contrib import admin

from .models import (
    AlertRule,
    AlertTrigger,
    Metric,
    MetricValue,
    PerformanceLog,
    SystemHealth,
)


@admin.register(Metric)
class MetricAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "metric_type",
        "value",
        "is_active",
        "last_updated",
    ]
    list_filter = [
        "metric_type",
        "is_active",
        "last_updated",
    ]
    search_fields = ["name", "description"]
    readonly_fields = ["last_updated"]


@admin.register(MetricValue)
class MetricValueAdmin(admin.ModelAdmin):
    list_display = [
        "metric",
        "value",
        "timestamp",
    ]
    list_filter = [
        "metric",
        "timestamp",
    ]
    search_fields = ["metric__name"]
    readonly_fields = ["timestamp"]
    ordering = ["-timestamp"]


@admin.register(SystemHealth)
class SystemHealthAdmin(admin.ModelAdmin):
    list_display = [
        "service_name",
        "is_healthy",
        "response_time_ms",
        "last_check",
    ]
    list_filter = [
        "is_healthy",
        "last_check",
    ]
    search_fields = ["service_name", "status_message"]
    readonly_fields = ["last_check"]


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "metric",
        "threshold_value",
        "comparison_operator",
        "severity",
        "is_active",
        "created_at",
    ]
    list_filter = [
        "is_active",
        "severity",
        "comparison_operator",
        "created_at",
    ]
    search_fields = ["name", "metric__name"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(AlertTrigger)
class AlertTriggerAdmin(admin.ModelAdmin):
    list_display = [
        "rule",
        "metric_value",
        "threshold_value",
        "is_resolved",
        "triggered_at",
    ]
    list_filter = [
        "is_resolved",
        "triggered_at",
        "rule__severity",
    ]
    search_fields = ["rule__name", "message"]
    readonly_fields = ["triggered_at"]
    ordering = ["-triggered_at"]


@admin.register(PerformanceLog)
class PerformanceLogAdmin(admin.ModelAdmin):
    list_display = [
        "endpoint",
        "method",
        "response_time_ms",
        "status_code",
        "user_id",
        "timestamp",
    ]
    list_filter = [
        "method",
        "status_code",
        "timestamp",
    ]
    search_fields = [
        "endpoint",
        "user_agent",
        "ip_address",
    ]
    readonly_fields = ["timestamp"]
    ordering = ["-timestamp"]
