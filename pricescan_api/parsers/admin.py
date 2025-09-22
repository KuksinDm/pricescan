from django.contrib import admin

from .models import ParserConfig, ParserLog, ParserTask


@admin.register(ParserTask)
class ParserTaskAdmin(admin.ModelAdmin):
    list_display = [
        "parser_type",
        "shop",
        "query",
        "status",
        "products_found",
        "products_created",
        "products_updated",
        "errors_count",
        "started_at",
        "completed_at",
        "created_at",
    ]
    list_filter = [
        "parser_type",
        "status",
        "shop",
        "created_at",
    ]
    search_fields = [
        "query",
        "shop__name",
        "error_message",
    ]
    readonly_fields = [
        "created_at",
        "updated_at",
        "started_at",
        "completed_at",
    ]
    ordering = ["-created_at"]


@admin.register(ParserLog)
class ParserLogAdmin(admin.ModelAdmin):
    list_display = [
        "task",
        "level",
        "message",
        "timestamp",
    ]
    list_filter = [
        "level",
        "timestamp",
        "task__parser_type",
        "task__shop",
    ]
    search_fields = [
        "message",
        "task__query",
    ]
    readonly_fields = ["timestamp"]
    ordering = ["-timestamp"]


@admin.register(ParserConfig)
class ParserConfigAdmin(admin.ModelAdmin):
    list_display = [
        "shop",
        "is_enabled",
        "parse_interval_hours",
        "max_products_per_run",
        "max_pages_per_run",
        "timeout_seconds",
        "max_retries",
    ]
    list_filter = [
        "is_enabled",
        "parse_interval_hours",
    ]
    search_fields = [
        "shop__name",
    ]
    readonly_fields = ["created_at", "updated_at"]
