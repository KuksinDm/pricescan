import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

from product.models import Product


class User(AbstractUser):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    telegram_id = models.BigIntegerField(
        unique=True, null=True, blank=True, db_index=True
    )
    telegram_username = models.CharField(max_length=255, null=True, blank=True)
    language_code = models.CharField(max_length=8, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["telegram_id"]),
            models.Index(fields=["uuid"]),
        ]


class UserFavorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorites")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "product"]


# class SearchHistory(models.Model):
#     user = models.ForeignKey(
#         User, on_delete=models.CASCADE, related_name="search_history"
#     )
#     query = models.CharField(max_length=500)
#     search_date = models.DateTimeField(auto_now_add=True)
#     results_count = models.PositiveIntegerField(default=0)

#     class Meta:
#         ordering = ["-search_date"]
