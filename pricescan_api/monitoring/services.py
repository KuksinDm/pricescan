import logging
from datetime import timedelta
from typing import Any, Dict, List

from django.db import transaction
from django.db.models import Avg
from django.utils import timezone

from .models import (
    AlertRule,
    AlertTrigger,
    Metric,
    MetricType,
    MetricValue,
    PerformanceLog,
    SystemHealth,
)

logger = logging.getLogger(__name__)


class MonitoringService:
    """Сервис для мониторинга системы"""

    @staticmethod
    def update_metric(name: str, value: float, labels: Dict = None) -> Metric:
        """Обновление метрики"""
        try:
            with transaction.atomic():
                metric, created = Metric.objects.get_or_create(
                    name=name, defaults={"value": value, "labels": labels or {}}
                )

                if not created:
                    metric.value = value
                    metric.labels = labels or metric.labels
                    metric.save(update_fields=["value", "labels"])

                # Сохраняем историческое значение
                MetricValue.objects.create(
                    metric=metric, value=value, labels=labels or {}
                )

                return metric
        except Exception as e:
            logger.error(f"Ошибка обновления метрики {name}: {e}")
            raise

    @staticmethod
    def increment_counter(
        name: str, increment: float = 1.0, labels: Dict = None
    ) -> Metric:
        """Увеличение счетчика"""
        try:
            with transaction.atomic():
                metric, created = Metric.objects.get_or_create(
                    name=name,
                    defaults={
                        "metric_type": MetricType.COUNTER,
                        "value": increment,
                        "labels": labels or {},
                    },
                )

                if not created:
                    metric.value += increment
                    metric.save(update_fields=["value"])

                # Сохраняем историческое значение
                MetricValue.objects.create(
                    metric=metric, value=metric.value, labels=labels or {}
                )

                return metric
        except Exception as e:
            logger.error(f"Ошибка увеличения счетчика {name}: {e}")
            raise

    @staticmethod
    def update_system_health(
        service_name: str,
        is_healthy: bool,
        status_message: str = "",
        response_time_ms: int = None,
        extra_data: Dict = None,
    ) -> SystemHealth:
        """Обновление состояния сервиса"""
        try:
            health, created = SystemHealth.objects.get_or_create(
                service_name=service_name,
                defaults={
                    "is_healthy": is_healthy,
                    "status_message": status_message,
                    "response_time_ms": response_time_ms,
                    "extra_data": extra_data or {},
                },
            )

            if not created:
                health.is_healthy = is_healthy
                health.status_message = status_message
                health.response_time_ms = response_time_ms
                health.extra_data = extra_data or health.extra_data
                health.save(
                    update_fields=[
                        "is_healthy",
                        "status_message",
                        "response_time_ms",
                        "extra_data",
                    ]
                )

            return health
        except Exception as e:
            logger.error(f"Ошибка обновления состояния сервиса {service_name}: {e}")
            raise

    @staticmethod
    def log_api_performance(
        endpoint: str,
        method: str,
        response_time_ms: int,
        status_code: int,
        user_id: int = None,
        ip_address: str = None,
        user_agent: str = "",
        request_size_bytes: int = None,
        response_size_bytes: int = None,
    ) -> PerformanceLog:
        """Логирование производительности API"""
        try:
            return PerformanceLog.objects.create(
                endpoint=endpoint,
                method=method,
                response_time_ms=response_time_ms,
                status_code=status_code,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                request_size_bytes=request_size_bytes,
                response_size_bytes=response_size_bytes,
            )
        except Exception as e:
            logger.error(f"Ошибка логирования производительности: {e}")
            raise

    @staticmethod
    def check_alert_rules() -> Dict[str, int]:
        """Проверка правил алертов"""
        try:
            active_rules = AlertRule.objects.filter(is_active=True).select_related(
                "metric"
            )
            triggered_count = 0

            for rule in active_rules:
                try:
                    if MonitoringService._should_trigger_rule(rule):
                        MonitoringService._trigger_rule(rule)
                        triggered_count += 1
                except Exception as e:
                    logger.error(f"Ошибка проверки правила {rule.id}: {e}")
                    continue

            logger.info(f"Проверка правил алертов: {triggered_count} сработало")
            return {"checked": active_rules.count(), "triggered": triggered_count}

        except Exception as e:
            logger.error(f"Ошибка проверки правил алертов: {e}")
            raise

    @staticmethod
    def _should_trigger_rule(rule: AlertRule) -> bool:
        """Проверка условия срабатывания правила"""
        metric_value = rule.metric.value

        if rule.comparison_operator == "gt":
            return metric_value > rule.threshold_value
        elif rule.comparison_operator == "gte":
            return metric_value >= rule.threshold_value
        elif rule.comparison_operator == "lt":
            return metric_value < rule.threshold_value
        elif rule.comparison_operator == "lte":
            return metric_value <= rule.threshold_value
        elif rule.comparison_operator == "eq":
            return metric_value == rule.threshold_value
        elif rule.comparison_operator == "ne":
            return metric_value != rule.threshold_value

        return False

    @staticmethod
    def _trigger_rule(rule: AlertRule):
        """Срабатывание правила"""
        try:
            # Проверяем, не срабатывало ли правило недавно
            recent_trigger = AlertTrigger.objects.filter(
                rule=rule,
                triggered_at__gte=timezone.now() - timedelta(minutes=5),
                is_resolved=False,
            ).first()

            if recent_trigger:
                return  # Не спамим уведомлениями

            # Создаем срабатывание
            AlertTrigger.objects.create(
                rule=rule,
                metric_value=rule.metric.value,
                threshold_value=rule.threshold_value,
                message=f"Метрика {rule.metric.name} = {rule.metric.value} {rule.comparison_operator} {rule.threshold_value}",
            )

            logger.info(f"Правило {rule.name} сработало")

        except Exception as e:
            logger.error(f"Ошибка срабатывания правила {rule.id}: {e}")
            raise

    @staticmethod
    def get_system_overview() -> Dict[str, Any]:
        """Общий обзор системы"""
        try:
            # Состояние сервисов
            services = SystemHealth.objects.all()
            healthy_services = services.filter(is_healthy=True).count()
            total_services = services.count()

            # Метрики
            total_metrics = Metric.objects.count()
            active_metrics = Metric.objects.filter(is_active=True).count()

            # Производительность за последний час
            hour_ago = timezone.now() - timedelta(hours=1)
            recent_logs = PerformanceLog.objects.filter(timestamp__gte=hour_ago)

            avg_response_time = (
                recent_logs.aggregate(avg_time=Avg("response_time_ms"))["avg_time"] or 0
            )

            error_rate = (
                recent_logs.filter(status_code__gte=400).count()
                / max(recent_logs.count(), 1)
                * 100
            )

            # Активные алерты
            active_alerts = AlertTrigger.objects.filter(is_resolved=False).count()

            return {
                "services": {
                    "total": total_services,
                    "healthy": healthy_services,
                    "unhealthy": total_services - healthy_services,
                    "health_percentage": (healthy_services / max(total_services, 1))
                    * 100,
                },
                "metrics": {"total": total_metrics, "active": active_metrics},
                "performance": {
                    "avg_response_time_ms": round(avg_response_time, 2),
                    "error_rate_percentage": round(error_rate, 2),
                    "requests_last_hour": recent_logs.count(),
                },
                "alerts": {"active_triggers": active_alerts},
            }

        except Exception as e:
            logger.error(f"Ошибка получения обзора системы: {e}")
            return {}

    @staticmethod
    def get_metric_history(
        metric_name: str, hours: int = 24, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """История метрики"""
        try:
            since = timezone.now() - timedelta(hours=hours)
            values = MetricValue.objects.filter(
                metric__name=metric_name, timestamp__gte=since
            ).order_by("-timestamp")[:limit]

            return [
                {
                    "value": value.value,
                    "timestamp": value.timestamp.isoformat(),
                    "labels": value.labels,
                }
                for value in values
            ]
        except Exception as e:
            logger.error(f"Ошибка получения истории метрики {metric_name}: {e}")
            return []

    @staticmethod
    def cleanup_old_data(days: int = 30):
        """Очистка старых данных"""
        try:
            cutoff_date = timezone.now() - timedelta(days=days)

            # Удаляем старые логи производительности
            deleted_logs = PerformanceLog.objects.filter(
                timestamp__lt=cutoff_date
            ).delete()[0]

            # Удаляем старые значения метрик
            deleted_metrics = MetricValue.objects.filter(
                timestamp__lt=cutoff_date
            ).delete()[0]

            # Удаляем старые срабатывания алертов
            deleted_triggers = AlertTrigger.objects.filter(
                triggered_at__lt=cutoff_date, is_resolved=True
            ).delete()[0]

            logger.info(
                f"Очистка данных: {deleted_logs} логов, {deleted_metrics} метрик, {deleted_triggers} триггеров"
            )

            return {
                "deleted_logs": deleted_logs,
                "deleted_metrics": deleted_metrics,
                "deleted_triggers": deleted_triggers,
            }

        except Exception as e:
            logger.error(f"Ошибка очистки данных: {e}")
            raise
