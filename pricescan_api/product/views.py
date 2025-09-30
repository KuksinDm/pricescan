from django.db.models import Count, Min, Q
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Offer, PriceAlert, PriceHistory, Product, Shop
from .serializers import (
    OfferSerializer,
    PriceAlertSerializer,
    PriceHistorySerializer,
    ProductSerializer,
    ShopSerializer,
)
from .tasks import (
    check_alerts_for_product,
    discover_products_for_shop,
    health_check_parsers,
    refresh_product,
    update_shop_products,
)


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductSerializer
    queryset = Product.objects.all()

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

    @extend_schema(summary="Все предложения по запросу (группировка по продуктам)")
    @action(detail=False, methods=["get"], url_path="cheapest")
    def cheapest(self, request):
        query = request.query_params.get("q")
        if not query:
            return Response({"detail": "Параметр q обязателен"}, status=400)

        # Находим все продукты по запросу
        products = self.get_queryset()
        if not products.exists():
            return Response({"detail": "Не найдено"}, status=404)

        # Для каждого продукта находим лучшее предложение
        results = []
        for product in products:
            best_offer = (
                Offer.objects.filter(product=product, is_available=True)
                .select_related("shop")
                .order_by("price")
                .first()
            )
            if best_offer:
                offer_data = OfferSerializer(best_offer).data
                # Добавляем количество всех предложений
                offer_data["total_offers"] = Offer.objects.filter(
                    product=product, is_available=True
                ).count()
                results.append(offer_data)

        # Сортируем по цене (самые дешевые первые)
        results.sort(key=lambda x: float(x["price"]))

        return Response(results, status=200)

    # @extend_schema(summary="Самое дешёвое предложение по запросу")
    # @action(detail=False, methods=["get"], url_path="cheapest")
    # def cheapest(self, request):
    #     query = request.query_params.get("q")
    #     if not query:
    #         return Response({"detail": "Параметр q обязателен"}, status=400)
    #     products = self.get_queryset()
    #     if not products.exists():
    #         return Response({"detail": "Не найдено"}, status=404)
    #     offer = (
    #         Offer.objects.filter(product__in=products, is_available=True)
    #         .select_related("shop", "product")
    #         .order_by("price")
    #         .first()
    #     )
    #     if not offer:
    #         return Response({"detail": "Нет предложений"}, status=404)
    #     return Response(OfferSerializer(offer).data, status=200)

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
    queryset = Offer.objects.all()

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
    queryset = PriceAlert.objects.all()

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


class PriceHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = PriceHistorySerializer
    queryset = PriceHistory.objects.all()

    def get_queryset(self):
        queryset = PriceHistory.objects.select_related("offer__product", "offer__shop")
        offer_id = self.request.query_params.get("offer")
        if offer_id and offer_id.isdigit():
            queryset = queryset.filter(offer_id=int(offer_id))
        return queryset.order_by("-timestamp")


class ShopViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = ShopSerializer
    queryset = Shop.objects.all()
    http_method_names = ["get"]

    @extend_schema(summary="Список активных магазинов")
    def list(self, request):
        shops = Shop.objects.filter(is_active=True)
        data = [
            {
                "id": shop.id,
                "name": shop.name,
                "domain": shop.domain,
                "parser_type": shop.parser_type,
                "is_active": shop.is_active,
            }
            for shop in shops
        ]
        return Response(data)

    @extend_schema(summary="Обновить все товары магазина")
    @action(detail=True, methods=["post"], url_path="refresh-products")
    def refresh_products(self, request, pk=None):
        """Обновить все товары конкретного магазина"""
        update_shop_products.delay(int(pk))
        return Response({"queued": True}, status=202)

    @extend_schema(summary="Найти новые товары в магазине")
    @action(detail=True, methods=["post"], url_path="discover")
    def discover_products(self, request, pk=None):
        """Найти новые товары в магазине"""
        query = request.data.get("query", "настольная игра")
        limit = request.data.get("limit", 50)

        discover_products_for_shop.delay(int(pk), query, limit)
        return Response({"queued": True}, status=202)

    @extend_schema(summary="Проверить здоровье парсеров")
    @action(detail=False, methods=["get"], url_path="health-check")
    def health_check(self, request):
        """Проверить здоровье всех парсеров"""
        result = health_check_parsers.delay()
        return Response({"task_id": result.id}, status=202)
