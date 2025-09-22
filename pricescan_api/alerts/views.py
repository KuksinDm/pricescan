from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from product.models import Product, Shop

from .models import Alert, AlertHistory
from .serializers import AlertHistorySerializer, AlertSerializer
from .services import AlertService


class AlertViewSet(ModelViewSet):
    """API для управления алертами пользователей"""

    serializer_class = AlertSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Alert.objects.filter(user=self.request.user)
            .select_related("product", "shop")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(summary="Создать алерт на снижение цены")
    def create(self, request, *args, **kwargs):
        """Создание нового алерта"""
        try:
            product_id = request.data.get("product")
            threshold_price = request.data.get("threshold_price")
            currency = request.data.get("currency", "RUB")
            shop_id = request.data.get("shop")
            alert_type = request.data.get("alert_type", "price_drop")

            if not product_id or not threshold_price:
                return Response(
                    {"error": "product и threshold_price обязательны"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                return Response(
                    {"error": "Продукт не найден"}, status=status.HTTP_404_NOT_FOUND
                )

            shop = None
            if shop_id:
                try:
                    shop = Shop.objects.get(id=shop_id)
                except Shop.DoesNotExist:
                    return Response(
                        {"error": "Магазин не найден"}, status=status.HTTP_404_NOT_FOUND
                    )

            alert = AlertService.create_alert(
                user=request.user,
                product=product,
                threshold_price=threshold_price,
                currency=currency,
                shop=shop,
                alert_type=alert_type,
            )

            return Response(AlertSerializer(alert).data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(summary="Переключить статус алерта")
    @action(detail=True, methods=["post"])
    def toggle(self, request, pk=None):
        """Переключение статуса алерта"""
        success = AlertService.toggle_alert(pk, request.user)
        if success:
            alert = self.get_object()
            return Response({
                "is_active": alert.is_active,
                "message": "Статус алерта изменен",
            })
        return Response({"error": "Алерт не найден"}, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(summary="Статистика алертов пользователя")
    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """Статистика алертов пользователя"""
        stats = AlertService.get_alert_statistics(request.user)
        return Response(stats)

    @extend_schema(summary="История срабатываний алерта")
    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        """История срабатываний конкретного алерта"""
        try:
            alert = self.get_object()
            history = AlertHistory.objects.filter(alert=alert).order_by("-triggered_at")
            serializer = AlertHistorySerializer(history, many=True)
            return Response(serializer.data)
        except Alert.DoesNotExist:
            return Response(
                {"error": "Алерт не найден"}, status=status.HTTP_404_NOT_FOUND
            )


class AlertHistoryViewSet(ModelViewSet):
    """API для истории алертов (только чтение)"""

    serializer_class = AlertHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            AlertHistory.objects.filter(alert__user=self.request.user)
            .select_related("alert", "shop")
            .order_by("-triggered_at")
        )
