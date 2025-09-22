from django.contrib import admin

from .models import Alert, AlertHistory


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "product",
        "shop",
        "alert_type",
        "threshold_price",
        "currency",
        "is_active",
        "is_triggered",
        "trigger_count",
        "created_at",
    ]
    list_filter = [
        "alert_type",
        "is_active",
        "is_triggered",
        "currency",
        "created_at",
    ]
    search_fields = [
        "user__username",
        "product__title",
        "shop__name",
    ]
    readonly_fields = ["created_at", "updated_at", "last_triggered_at"]
    ordering = ["-created_at"]


@admin.register(AlertHistory)
class AlertHistoryAdmin(admin.ModelAdmin):
    list_display = [
        "alert",
        "triggered_at",
        "old_price",
        "new_price",
        "currency",
        "shop",
    ]
    list_filter = [
        "triggered_at",
        "currency",
        "shop",
    ]
    search_fields = [
        "alert__user__username",
        "alert__product__title",
        "shop__name",
    ]
    readonly_fields = ["triggered_at"]
    ordering = ["-triggered_at"]
