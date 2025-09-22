from django.db import models
from django.utils import timezone


class ParserType(models.TextChoices):
    """Типы парсеров"""

    BEAUTIFULSOUP = "beautifulsoup", "BeautifulSoup"
    PLAYWRIGHT = "playwright", "Playwright"
    API_JSON = "api_json", "API JSON"


class ParserStatus(models.TextChoices):
    """Статусы парсинга"""

    PENDING = "pending", "Ожидает"
    RUNNING = "running", "Выполняется"
    COMPLETED = "completed", "Завершен"
    FAILED = "failed", "Ошибка"
    CANCELLED = "cancelled", "Отменен"


class ParserTask(models.Model):
    """Задача парсинга"""

    parser_type = models.CharField(max_length=20, choices=ParserType.choices)
    shop = models.ForeignKey(
        "product.Shop", on_delete=models.CASCADE, related_name="parser_tasks"
    )

    # Параметры задачи
    query = models.CharField(max_length=500, blank=True, help_text="Поисковый запрос")
    category_url = models.URLField(blank=True, help_text="URL категории для парсинга")
    max_products = models.PositiveIntegerField(default=50)
    max_pages = models.PositiveIntegerField(default=2)

    # Статус и результаты
    status = models.CharField(
        max_length=20, choices=ParserStatus.choices, default=ParserStatus.PENDING
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Результаты
    products_found = models.PositiveIntegerField(default=0)
    products_created = models.PositiveIntegerField(default=0)
    products_updated = models.PositiveIntegerField(default=0)
    errors_count = models.PositiveIntegerField(default=0)

    # Ошибки
    error_message = models.TextField(blank=True)
    error_traceback = models.TextField(blank=True)

    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["parser_type", "status"]),
            models.Index(fields=["shop", "status"]),
        ]
        verbose_name = "Задача парсинга"
        verbose_name_plural = "Задачи парсинга"

    def __str__(self):
        return f"{self.get_parser_type_display()} - {self.shop.name} - {self.status}"

    def start(self):
        """Запуск задачи"""
        self.status = ParserStatus.RUNNING
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at"])

    def complete(
        self, products_found=0, products_created=0, products_updated=0, errors_count=0
    ):
        """Завершение задачи"""
        self.status = ParserStatus.COMPLETED
        self.completed_at = timezone.now()
        self.products_found = products_found
        self.products_created = products_created
        self.products_updated = products_updated
        self.errors_count = errors_count
        self.save(
            update_fields=[
                "status",
                "completed_at",
                "products_found",
                "products_created",
                "products_updated",
                "errors_count",
            ]
        )

    def fail(self, error_message="", error_traceback=""):
        """Ошибка задачи"""
        self.status = ParserStatus.FAILED
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.error_traceback = error_traceback
        self.save(
            update_fields=["status", "completed_at", "error_message", "error_traceback"]
        )

    @property
    def duration(self):
        """Длительность выполнения"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None


class ParserLog(models.Model):
    """Лог парсинга"""

    task = models.ForeignKey(ParserTask, on_delete=models.CASCADE, related_name="logs")
    level = models.CharField(
        max_length=10,
        choices=[
            ("DEBUG", "Debug"),
            ("INFO", "Info"),
            ("WARNING", "Warning"),
            ("ERROR", "Error"),
            ("CRITICAL", "Critical"),
        ],
    )
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["task", "timestamp"]),
            models.Index(fields=["level", "timestamp"]),
        ]
        verbose_name = "Лог парсинга"
        verbose_name_plural = "Логи парсинга"

    def __str__(self):
        return f"{self.level} - {self.timestamp.strftime('%H:%M:%S')} - {self.message[:50]}"


class ParserConfig(models.Model):
    """Конфигурация парсеров"""

    shop = models.OneToOneField(
        "product.Shop", on_delete=models.CASCADE, related_name="parser_config"
    )

    # Настройки парсинга
    is_enabled = models.BooleanField(default=True)
    parse_interval_hours = models.PositiveIntegerField(
        default=24, help_text="Интервал парсинга в часах"
    )
    max_products_per_run = models.PositiveIntegerField(default=100)
    max_pages_per_run = models.PositiveIntegerField(default=5)
    timeout_seconds = models.PositiveIntegerField(default=300)

    # Настройки retry
    max_retries = models.PositiveIntegerField(default=3)
    retry_delay_seconds = models.PositiveIntegerField(default=60)

    # Дополнительные параметры
    custom_headers = models.JSONField(default=dict, blank=True)
    custom_params = models.JSONField(default=dict, blank=True)

    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Конфигурация парсера"
        verbose_name_plural = "Конфигурации парсеров"

    def __str__(self):
        return f"Config for {self.shop.name}"
