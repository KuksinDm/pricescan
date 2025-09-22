from django.conf import settings
from django.db import models
from django.utils import timezone


class AlertType(models.TextChoices):
    """Типы алертов"""

    PRICE_DROP = "price_drop", "Снижение цены"
    PRICE_RISE = "price_rise", "Повышение цены"
    AVAILABILITY = "availability", "Появление в наличии"
    CUSTOM = "custom", "Пользовательский"


class Alert(models.Model):
    """Модель для алертов пользователей"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="alerts"
    )
    product = models.ForeignKey(
        "product.Product", on_delete=models.CASCADE, related_name="alerts"
    )
    shop = models.ForeignKey(
        "product.Shop",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Конкретный магазин (если не указан, то по всем магазинам)",
    )

    # Настройки алерта
    alert_type = models.CharField(
        max_length=20, choices=AlertType.choices, default=AlertType.PRICE_DROP
    )
    threshold_price = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Пороговая цена для срабатывания"
    )
    currency = models.CharField(max_length=3, default="RUB")

    # Статус
    is_active = models.BooleanField(default=True)
    is_triggered = models.BooleanField(default=False)
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    trigger_count = models.PositiveIntegerField(default=0)

    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["user", "product", "shop", "alert_type", "threshold_price"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["product", "is_active"]),
            models.Index(fields=["is_active", "is_triggered"]),
            models.Index(fields=["created_at"]),
        ]
        verbose_name = "Алерт"
        verbose_name_plural = "Алерты"

    def __str__(self):
        return f"{self.user.username} - {self.product.title} - {self.threshold_price} {self.currency}"

    def trigger(self):
        """Срабатывание алерта"""
        self.is_triggered = True
        self.last_triggered_at = timezone.now()
        self.trigger_count += 1
        self.save(update_fields=["is_triggered", "last_triggered_at", "trigger_count"])


class AlertHistory(models.Model):
    """История срабатываний алертов"""

    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, related_name="history")
    triggered_at = models.DateTimeField(auto_now_add=True)
    old_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    new_price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="RUB")
    shop = models.ForeignKey(
        "product.Shop", on_delete=models.CASCADE, null=True, blank=True
    )
    message = models.TextField(blank=True, help_text="Сообщение пользователю")

    class Meta:
        indexes = [
            models.Index(fields=["alert", "triggered_at"]),
            models.Index(fields=["triggered_at"]),
        ]
        verbose_name = "История алерта"
        verbose_name_plural = "История алертов"

    def __str__(self):
        return f"{self.alert} - {self.triggered_at.strftime('%d.%m.%Y %H:%M')}"
