from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .models import AlertRule, AlertTrigger, Metric, PerformanceLog, SystemHealth
from .serializers import (
    AlertRuleSerializer,
    AlertTriggerSerializer,
    MetricSerializer,
    PerformanceLogSerializer,
    SystemHealthSerializer,
)
from .services import MonitoringService


class MetricViewSet(ModelViewSet):
    """API для управления метриками"""

    serializer_class = MetricSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Metric.objects.all().order_by("name")

    @extend_schema(summary="Обновить значение метрики")
    @action(detail=False, methods=["post"])
    def update_value(self, request):
        """Обновление значения метрики"""
        name = request.data.get("name")
        value = request.data.get("value")
        labels = request.data.get("labels", {})

        if not name or value is None:
            return Response(
                {"error": "name и value обязательны"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            metric = MonitoringService.update_metric(name, value, labels)
            return Response(MetricSerializer(metric).data)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(summary="Увеличить счетчик")
    @action(detail=False, methods=["post"])
    def increment_counter(self, request):
        """Увеличение счетчика"""
        name = request.data.get("name")
        increment = request.data.get("increment", 1.0)
        labels = request.data.get("labels", {})

        if not name:
            return Response(
                {"error": "name обязателен"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            metric = MonitoringService.increment_counter(name, increment, labels)
            return Response(MetricSerializer(metric).data)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(summary="История метрики")
    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        """История значений метрики"""
        hours = int(request.query_params.get("hours", 24))
        limit = int(request.query_params.get("limit", 100))

        try:
            metric = self.get_object()
            history = MonitoringService.get_metric_history(metric.name, hours, limit)
            return Response(history)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SystemHealthViewSet(ModelViewSet):
    """API для состояния системы"""

    serializer_class = SystemHealthSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SystemHealth.objects.all().order_by("service_name")

    @extend_schema(summary="Обновить состояние сервиса")
    @action(detail=False, methods=["post"])
    def update_health(self, request):
        """Обновление состояния сервиса"""
        service_name = request.data.get("service_name")
        is_healthy = request.data.get("is_healthy", True)
        status_message = request.data.get("status_message", "")
        response_time_ms = request.data.get("response_time_ms")
        extra_data = request.data.get("extra_data", {})

        if not service_name:
            return Response(
                {"error": "service_name обязателен"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            health = MonitoringService.update_system_health(
                service_name, is_healthy, status_message, response_time_ms, extra_data
            )
            return Response(SystemHealthSerializer(health).data)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AlertRuleViewSet(ModelViewSet):
    """API для правил алертов"""

    serializer_class = AlertRuleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AlertRule.objects.all().select_related("metric").order_by("name")

    @extend_schema(summary="Проверить правила алертов")
    @action(detail=False, methods=["post"])
    def check_rules(self, request):
        """Проверка всех правил алертов"""
        try:
            result = MonitoringService.check_alert_rules()
            return Response(result)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AlertTriggerViewSet(ReadOnlyModelViewSet):
    """API для срабатываний алертов (только чтение)"""

    serializer_class = AlertTriggerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            AlertTrigger.objects.all()
            .select_related("rule", "rule__metric")
            .order_by("-triggered_at")
        )


class PerformanceLogViewSet(ReadOnlyModelViewSet):
    """API для логов производительности (только чтение)"""

    serializer_class = PerformanceLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PerformanceLog.objects.all().order_by("-timestamp")


class SystemOverviewViewSet(ReadOnlyModelViewSet):
    """API для общего обзора системы"""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Общий обзор системы")
    def list(self, request):
        """Получение общего обзора системы"""
        try:
            overview = MonitoringService.get_system_overview()
            return Response(overview)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(summary="Очистка старых данных")
    @action(detail=False, methods=["post"])
    def cleanup(self, request):
        """Очистка старых данных"""
        days = int(request.data.get("days", 30))

        try:
            result = MonitoringService.cleanup_old_data(days)
            return Response(result)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
