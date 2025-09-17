from django.db.models import Count, Min, Q
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Offer, PriceAlert, Product
from .serializers import (
    OfferSerializer,
    PriceAlertSerializer,
    ProductSerializer,
)
from .tasks import check_alerts_for_product, refresh_product


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductSerializer

    def get_queryset(self):
        queryset = Product.objects.select_related(
            "author", "publisher", "category"
        ).annotate(
            min_price=Min("offers__price", filter=Q(offers__is_available=True)),
            offers_count=Count("offers", distinct=True),
        )
        query = self.request.query_params.get("q")
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(author__name__icontains=query)
                | Q(brand__icontains=query)
                | Q(ean__icontains=query)
            )
        # простые фильтры по id
        for field in ("author", "publisher", "category", "min_age"):
            value = self.request.query_params.get(field)
            if value and value.isdigit():
                queryset = queryset.filter(**{field: int(value)})
        return queryset.order_by("title")

    @extend_schema(summary="Самое дешёвое предложение по запросу")
    @action(detail=False, methods=["get"], url_path="cheapest")
    def cheapest(self, request):
        query = request.query_params.get("q")
        if not query:
            return Response({"detail": "Параметр q обязателен"}, status=400)
        products = self.get_queryset()
        if not products.exists():
            return Response({"detail": "Не найдено"}, status=404)
        offer = (
            Offer.objects.filter(product__in=products, is_available=True)
            .select_related("shop", "product")
            .order_by("price")
            .first()
        )
        if not offer:
            return Response({"detail": "Нет предложений"}, status=404)
        return Response(OfferSerializer(offer).data, status=200)

    @extend_schema(summary="Обновить цены по продукту (запуск задачи)")
    @action(
        detail=True,
        methods=["post"],
        url_path="refresh",
        permission_classes=[permissions.IsAuthenticated],
    )
    def refresh(self, request, pk=None):
        refresh_product.delay(int(pk))
        return Response({"queued": True}, status=202)


class OfferViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = OfferSerializer

    def get_queryset(self):
        queryset = Offer.objects.select_related("product", "shop")
        product_id = self.request.query_params.get("product")
        shop_id = self.request.query_params.get("shop")
        if product_id and product_id.isdigit():
            queryset = queryset.filter(product_id=int(product_id))
        if shop_id and shop_id.isdigit():
            queryset = queryset.filter(shop_id=int(shop_id))
        is_available = self.request.query_params.get("is_available")
        if is_available is not None:
            value = str(is_available).lower() in {"1", "true", "yes", "y"}
            queryset = queryset.filter(is_available=value)
        ordering = self.request.query_params.get("ordering", "price")
        if ordering.lstrip("-") in {"price", "last_updated"}:
            queryset = queryset.order_by(ordering)
        return queryset


class PriceAlertViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PriceAlertSerializer

    def get_queryset(self):
        return PriceAlert.objects.filter(user=self.request.user).select_related(
            "product", "shop"
        )

    def perform_create(self, serializer):
        obj = serializer.save(user=self.request.user, is_active=True)
        # сразу проверить после создания (асинхронно)
        check_alerts_for_product.delay(obj.product_id)

    @extend_schema(summary="Активировать/деактивировать алёрт")
    @action(detail=True, methods=["post"], url_path="toggle")
    def toggle(self, request, pk=None):
        alert = self.get_object()
        alert.is_active = not alert.is_active
        alert.save(update_fields=["is_active"])
        return Response({"is_active": alert.is_active}, status=200)
