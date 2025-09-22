import logging
from datetime import timedelta

from celery import shared_task
from django.db.models import Avg, Count, Q
from django.utils import timezone

from alerts.services import AlertService

from .services import MonitoringService

logger = logging.getLogger(__name__)


@shared_task(queue="monitoring")
def check_system_health():
    """Проверка состояния системы"""
    try:
        logger.info("Запуск проверки состояния системы")

        # Проверяем состояние основных сервисов
        services_to_check = ["database", "redis", "celery", "parsers", "telegram_bot"]

        for service in services_to_check:
            try:
                # Здесь можно добавить реальные проверки
                # Например, ping базы данных, Redis и т.д.
                is_healthy = True  # Заглушка
                status_message = "OK"
                response_time_ms = 100  # Заглушка

                MonitoringService.update_system_health(
                    service_name=service,
                    is_healthy=is_healthy,
                    status_message=status_message,
                    response_time_ms=response_time_ms,
                )

            except Exception as e:
                logger.error(f"Ошибка проверки сервиса {service}: {e}")
                MonitoringService.update_system_health(
                    service_name=service, is_healthy=False, status_message=str(e)
                )

        logger.info("Проверка состояния системы завершена")
        return {"status": "completed"}

    except Exception as e:
        logger.error(f"Ошибка проверки состояния системы: {e}")
        raise


@shared_task(queue="monitoring")
def check_alert_rules():
    """Проверка правил алертов мониторинга"""
    try:
        logger.info("Запуск проверки правил алертов")
        result = MonitoringService.check_alert_rules()
        logger.info(f"Проверка правил алертов завершена: {result}")
        return result
    except Exception as e:
        logger.error(f"Ошибка проверки правил алертов: {e}")
        raise


@shared_task(queue="monitoring")
def check_price_alerts():
    """Проверка алертов цен"""
    try:
        logger.info("Запуск проверки алертов цен")
        result = AlertService.check_all_alerts()
        logger.info(f"Проверка алертов цен завершена: {result}")
        return result
    except Exception as e:
        logger.error(f"Ошибка проверки алертов цен: {e}")
        raise


@shared_task(queue="monitoring")
def cleanup_monitoring_data():
    """Очистка старых данных мониторинга"""
    try:
        logger.info("Запуск очистки данных мониторинга")
        result = MonitoringService.cleanup_old_data(days=30)
        logger.info(f"Очистка данных мониторинга завершена: {result}")
        return result
    except Exception as e:
        logger.error(f"Ошибка очистки данных мониторинга: {e}")
        raise


@shared_task(queue="monitoring")
def update_system_metrics():
    """Обновление системных метрик"""
    try:
        logger.info("Запуск обновления системных метрик")

        from django.core.cache import cache
        from django.db import connection

        # Метрики базы данных
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM product_product")
            product_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM product_offer")
            offer_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM alerts_alert")
            alert_count = cursor.fetchone()[0]

        # Обновляем метрики
        MonitoringService.update_metric("products_total", product_count)
        MonitoringService.update_metric("offers_total", offer_count)
        MonitoringService.update_metric("alerts_total", alert_count)

        # Метрики кэша
        cache_stats = cache.get_stats()
        if cache_stats:
            MonitoringService.update_metric("cache_hits", cache_stats.get("hits", 0))
            MonitoringService.update_metric(
                "cache_misses", cache_stats.get("misses", 0)
            )

        logger.info("Обновление системных метрик завершено")
        return {"status": "completed"}

    except Exception as e:
        logger.error(f"Ошибка обновления системных метрик: {e}")
        raise


@shared_task(queue="monitoring")
def generate_daily_report():
    """Генерация ежедневного отчета"""
    try:
        logger.info("Генерация ежедневного отчета")

        # Получаем обзор системы
        overview = MonitoringService.get_system_overview()

        # Статистика за последние 24 часа
        yesterday = timezone.now() - timedelta(days=1)

        from monitoring.models import PerformanceLog

        daily_stats = PerformanceLog.objects.filter(timestamp__gte=yesterday).aggregate(
            total_requests=Count("id"),
            avg_response_time=Avg("response_time_ms"),
            error_requests=Count("id", filter=Q(status_code__gte=400)),
        )

        report = {
            "date": timezone.now().date().isoformat(),
            "system_overview": overview,
            "daily_stats": daily_stats,
        }

        logger.info(f"Ежедневный отчет сгенерирован: {report}")
        return report

    except Exception as e:
        logger.error(f"Ошибка генерации ежедневного отчета: {e}")
        raise
