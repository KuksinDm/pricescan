import logging
import time

from django.utils.deprecation import MiddlewareMixin

from .services import MonitoringService

logger = logging.getLogger(__name__)


class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """Middleware для мониторинга производительности API"""

    def process_request(self, request):
        """Обработка входящего запроса"""
        request._start_time = time.time()
        request._request_size = len(request.body) if hasattr(request, "body") else 0

    def process_response(self, request, response):
        """Обработка исходящего ответа"""
        try:
            if hasattr(request, "_start_time"):
                # Вычисляем время ответа
                response_time_ms = int((time.time() - request._start_time) * 1000)

                # Получаем размер ответа
                response_size = (
                    len(response.content) if hasattr(response, "content") else 0
                )

                # Логируем производительность
                MonitoringService.log_api_performance(
                    endpoint=request.path,
                    method=request.method,
                    response_time_ms=response_time_ms,
                    status_code=response.status_code,
                    user_id=(
                        getattr(request.user, "id", None)
                        if hasattr(request, "user")
                        else None
                    ),
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get("HTTP_USER_AGENT", ""),
                    request_size_bytes=getattr(request, "_request_size", 0),
                    response_size_bytes=response_size,
                )

                # Обновляем метрики
                MonitoringService.increment_counter(
                    "api_requests_total",
                    labels={
                        "method": request.method,
                        "endpoint": request.path,
                        "status_code": str(response.status_code),
                    },
                )

                MonitoringService.update_metric(
                    "api_response_time_ms",
                    response_time_ms,
                    labels={
                        "method": request.method,
                        "endpoint": request.path,
                    },
                )

        except Exception as e:
            logger.error(f"Ошибка в PerformanceMonitoringMiddleware: {e}")

        return response

    def _get_client_ip(self, request):
        """Получение IP адреса клиента"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip
