from django.db import models


class MetricType(models.TextChoices):
    """Типы метрик"""

    COUNTER = "counter", "Счетчик"
    GAUGE = "gauge", "Измеритель"
    HISTOGRAM = "histogram", "Гистограмма"
    SUMMARY = "summary", "Сводка"


class Metric(models.Model):
    """Модель для метрик системы"""

    name = models.CharField(max_length=100, unique=True)
    metric_type = models.CharField(
        max_length=20, choices=MetricType.choices, default=MetricType.GAUGE
    )
    description = models.TextField(blank=True)
    labels = models.JSONField(default=dict, blank=True, help_text="Метки метрики")

    # Значения
    value = models.FloatField(default=0.0)
    last_updated = models.DateTimeField(auto_now=True)

    # Настройки
    is_active = models.BooleanField(default=True)
    unit = models.CharField(max_length=20, blank=True, help_text="Единица измерения")

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["metric_type"]),
            models.Index(fields=["is_active"]),
        ]
        verbose_name = "Метрика"
        verbose_name_plural = "Метрики"

    def __str__(self):
        return f"{self.name} ({self.get_metric_type_display()})"


class MetricValue(models.Model):
    """Исторические значения метрик"""

    metric = models.ForeignKey(Metric, on_delete=models.CASCADE, related_name="values")
    value = models.FloatField()
    labels = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["metric", "timestamp"]),
            models.Index(fields=["timestamp"]),
        ]
        verbose_name = "Значение метрики"
        verbose_name_plural = "Значения метрик"

    def __str__(self):
        return f"{self.metric.name}: {self.value} at {self.timestamp}"


class SystemHealth(models.Model):
    """Состояние системы"""

    service_name = models.CharField(max_length=50)
    is_healthy = models.BooleanField(default=True)
    status_message = models.TextField(blank=True)
    last_check = models.DateTimeField(auto_now=True)
    response_time_ms = models.PositiveIntegerField(null=True, blank=True)

    # Дополнительные данные
    extra_data = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ["service_name"]
        indexes = [
            models.Index(fields=["service_name"]),
            models.Index(fields=["is_healthy"]),
            models.Index(fields=["last_check"]),
        ]
        verbose_name = "Состояние сервиса"
        verbose_name_plural = "Состояния сервисов"

    def __str__(self):
        status = "✓" if self.is_healthy else "✗"
        return f"{status} {self.service_name}"


class AlertRule(models.Model):
    """Правила алертов для мониторинга"""

    name = models.CharField(max_length=100)
    metric = models.ForeignKey(
        Metric, on_delete=models.CASCADE, related_name="alert_rules"
    )

    # Условия срабатывания
    threshold_value = models.FloatField()
    comparison_operator = models.CharField(
        max_length=10,
        choices=[
            ("gt", "Больше"),
            ("gte", "Больше или равно"),
            ("lt", "Меньше"),
            ("lte", "Меньше или равно"),
            ("eq", "Равно"),
            ("ne", "Не равно"),
        ],
    )

    # Настройки алерта
    is_active = models.BooleanField(default=True)
    severity = models.CharField(
        max_length=20,
        choices=[
            ("low", "Низкий"),
            ("medium", "Средний"),
            ("high", "Высокий"),
            ("critical", "Критический"),
        ],
        default="medium",
    )

    # Уведомления
    notification_channels = models.JSONField(
        default=list,
        blank=True,
        help_text="Каналы уведомлений (email, telegram, webhook)",
    )

    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["severity"]),
        ]
        verbose_name = "Правило алерта"
        verbose_name_plural = "Правила алертов"

    def __str__(self):
        return f"{self.name} - {self.metric.name}"


class AlertTrigger(models.Model):
    """Срабатывания алертов мониторинга"""

    rule = models.ForeignKey(
        AlertRule, on_delete=models.CASCADE, related_name="triggers"
    )
    triggered_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    is_resolved = models.BooleanField(default=False)

    # Данные срабатывания
    metric_value = models.FloatField()
    threshold_value = models.FloatField()
    message = models.TextField()

    class Meta:
        indexes = [
            models.Index(fields=["rule", "triggered_at"]),
            models.Index(fields=["is_resolved"]),
            models.Index(fields=["triggered_at"]),
        ]
        verbose_name = "Срабатывание алерта"
        verbose_name_plural = "Срабатывания алертов"

    def __str__(self):
        return f"{self.rule.name} - {self.triggered_at}"


class PerformanceLog(models.Model):
    """Лог производительности API"""

    endpoint = models.CharField(max_length=200)
    method = models.CharField(max_length=10)
    response_time_ms = models.PositiveIntegerField()
    status_code = models.PositiveIntegerField()
    user_id = models.PositiveIntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    # Дополнительные данные
    request_size_bytes = models.PositiveIntegerField(null=True, blank=True)
    response_size_bytes = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["endpoint", "timestamp"]),
            models.Index(fields=["method", "timestamp"]),
            models.Index(fields=["status_code", "timestamp"]),
            models.Index(fields=["timestamp"]),
        ]
        verbose_name = "Лог производительности"
        verbose_name_plural = "Логи производительности"

    def __str__(self):
        return f"{self.method} {self.endpoint} - {self.response_time_ms}ms"
