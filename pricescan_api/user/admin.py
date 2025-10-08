from django.contrib import admin

from .models import User, UserFavorite


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "telegram_id", "is_active", "is_staff")
    search_fields = ("username", "telegram_id", "email")


# @admin.register(SearchHistory)
# class SearchHistoryAdmin(admin.ModelAdmin):
#     list_display = ("id", "user", "query", "search_date", "results_count")
#     search_fields = ("user__username", "query")
#     autocomplete_fields = ("user",)
#     ordering = ("-search_date",)


@admin.register(UserFavorite)
class UserFavoriteAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "product", "added_at")
    search_fields = ("user__username", "product__title")
    autocomplete_fields = ("user", "product")
    ordering = ("-added_at",)
