from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import AlertRule, Metric, MetricType, SystemHealth
from .services import MonitoringService

User = get_user_model()


class MetricModelTest(TestCase):
    """Тесты для модели Metric"""

    def test_create_metric(self):
        """Тест создания метрики"""
        metric = Metric.objects.create(
            name="test_metric",
            metric_type=MetricType.GAUGE,
            value=100.0,
            description="Test metric",
        )

        self.assertEqual(metric.name, "test_metric")
        self.assertEqual(metric.metric_type, MetricType.GAUGE)
        self.assertEqual(metric.value, 100.0)
        self.assertTrue(metric.is_active)

    def test_metric_str(self):
        """Тест строкового представления метрики"""
        metric = Metric.objects.create(
            name="test_metric", metric_type=MetricType.COUNTER
        )

        expected = "test_metric (Счетчик)"
        self.assertEqual(str(metric), expected)


class SystemHealthModelTest(TestCase):
    """Тесты для модели SystemHealth"""

    def test_create_system_health(self):
        """Тест создания записи о состоянии системы"""
        health = SystemHealth.objects.create(
            service_name="test_service",
            is_healthy=True,
            status_message="OK",
            response_time_ms=100,
        )

        self.assertEqual(health.service_name, "test_service")
        self.assertTrue(health.is_healthy)
        self.assertEqual(health.status_message, "OK")
        self.assertEqual(health.response_time_ms, 100)

    def test_system_health_str(self):
        """Тест строкового представления состояния системы"""
        health = SystemHealth.objects.create(
            service_name="test_service", is_healthy=True
        )

        expected = "✓ test_service"
        self.assertEqual(str(health), expected)


class MonitoringServiceTest(TestCase):
    """Тесты для MonitoringService"""

    def test_update_metric(self):
        """Тест обновления метрики"""
        metric = MonitoringService.update_metric(
            name="test_metric", value=150.0, labels={"label1": "value1"}
        )

        self.assertEqual(metric.name, "test_metric")
        self.assertEqual(metric.value, 150.0)
        self.assertEqual(metric.labels, {"label1": "value1"})

    def test_increment_counter(self):
        """Тест увеличения счетчика"""
        # Создаем счетчик
        metric = MonitoringService.increment_counter("test_counter", 5.0)
        self.assertEqual(metric.value, 5.0)

        # Увеличиваем счетчик
        metric = MonitoringService.increment_counter("test_counter", 3.0)
        self.assertEqual(metric.value, 8.0)

    def test_update_system_health(self):
        """Тест обновления состояния системы"""
        health = MonitoringService.update_system_health(
            service_name="test_service",
            is_healthy=True,
            status_message="OK",
            response_time_ms=100,
        )

        self.assertEqual(health.service_name, "test_service")
        self.assertTrue(health.is_healthy)
        self.assertEqual(health.status_message, "OK")

    def test_get_system_overview(self):
        """Тест получения общего обзора системы"""
        # Создаем тестовые данные
        MonitoringService.update_metric("test_metric", 100.0)
        MonitoringService.update_system_health("test_service", True)

        overview = MonitoringService.get_system_overview()

        self.assertIn("services", overview)
        self.assertIn("metrics", overview)
        self.assertIn("performance", overview)
        self.assertIn("alerts", overview)

    def test_cleanup_old_data(self):
        """Тест очистки старых данных"""
        # Создаем тестовые данные
        metric = MonitoringService.update_metric("test_metric", 100.0)

        # Имитируем старые данные
        from datetime import timedelta

        from django.utils import timezone

        old_date = timezone.now() - timedelta(days=35)

        from .models import MetricValue, PerformanceLog

        MetricValue.objects.create(metric=metric, value=50.0, timestamp=old_date)
        PerformanceLog.objects.create(
            endpoint="/test",
            method="GET",
            response_time_ms=100,
            status_code=200,
            timestamp=old_date,
        )

        result = MonitoringService.cleanup_old_data(days=30)

        self.assertIn("deleted_metrics", result)
        self.assertIn("deleted_logs", result)


class AlertRuleModelTest(TestCase):
    """Тесты для модели AlertRule"""

    def setUp(self):
        self.metric = Metric.objects.create(
            name="test_metric", metric_type=MetricType.GAUGE, value=100.0
        )

    def test_create_alert_rule(self):
        """Тест создания правила алерта"""
        rule = AlertRule.objects.create(
            name="test_rule",
            metric=self.metric,
            threshold_value=150.0,
            comparison_operator="gt",
            severity="medium",
        )

        self.assertEqual(rule.name, "test_rule")
        self.assertEqual(rule.metric, self.metric)
        self.assertEqual(rule.threshold_value, 150.0)
        self.assertEqual(rule.comparison_operator, "gt")
        self.assertEqual(rule.severity, "medium")
        self.assertTrue(rule.is_active)

    def test_alert_rule_str(self):
        """Тест строкового представления правила алерта"""
        rule = AlertRule.objects.create(
            name="test_rule",
            metric=self.metric,
            threshold_value=150.0,
            comparison_operator="gt",
        )

        expected = "test_rule - test_metric"
        self.assertEqual(str(rule), expected)
