from datetime import datetime, timedelta

from django.db.models import Count, F, Min, OuterRef, Q, Subquery
from django.db.models.expressions import Window
from django.db.models.functions import RowNumber
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Offer, PriceAlert, PriceHistory, Product, Shop
from .serializers import (
    OfferSerializer,
    PriceAlertSerializer,
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


@extend_schema(tags=["products"])
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductSerializer
    queryset = Product.objects.all()

    @extend_schema(
        summary="Поиск товаров",
        description="Поиск настольных игр по названию, издателю или категории",
        tags=["products"],
        parameters=[
            OpenApiParameter(
                name="q",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Поисковый запрос",
            ),
            OpenApiParameter(
                name="publisher",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="ID издателя",
            ),
            OpenApiParameter(
                name="category",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="ID категории",
            ),
            OpenApiParameter(
                name="min_age",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Минимальный возраст",
            ),
        ],
    )
    def get_queryset(self):
        queryset = (
            Product.objects.prefetch_related("offers", "offers__shop")
            .select_related()
            .annotate(
                min_price=Min("offers__price"),
                offers_count=Count("offers", distinct=True),
            )
        )
        query = self.request.query_params.get("q")
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(publishers__name__icontains=query)
                | Q(categories__name__icontains=query)
            )
        for field in ("publisher", "category", "min_age"):
            value = self.request.query_params.get(field)
            if value and value.isdigit():
                if field == "publisher":
                    queryset = queryset.filter(publishers=int(value))
                elif field == "category":
                    queryset = queryset.filter(categories=int(value))
                else:
                    queryset = queryset.filter(**{field: int(value)})
        return queryset.order_by("title")

    @extend_schema(
        summary="Самые дешевые предложения",
        description="Находит все товары по запросу и показывает "
        "самое дешевое предложение для каждого",
        tags=["products"],
        parameters=[
            OpenApiParameter(
                name="q",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Поисковый запрос",
                required=True,
            ),
        ],
    )
    @action(detail=False, methods=["get"], url_path="cheapest")
    def cheapest(self, request):
        query = request.query_params.get("q")
        if not query:
            return Response({"detail": "Параметр q обязателен"}, status=400)

        products = Product.objects.prefetch_related("offers", "offers__shop").annotate(
            min_price=Min("offers__price"), offers_count=Count("offers", distinct=True)
        )
        products = products.filter(
            Q(title__icontains=query)
            | Q(publishers__name__icontains=query)
            | Q(categories__name__icontains=query)
        ).order_by("title")

        product_ids_sq = products.values("id")

        offers_count_sq = (
            Offer.objects.filter(product_id=OuterRef("product_id"), is_available=True)
            .values("product_id")
            .annotate(c=Count("id"))
            .values("c")[:1]
        )

        best_offers = (
            Offer.objects.filter(is_available=True, product_id__in=product_ids_sq)
            .annotate(
                rn=Window(
                    expression=RowNumber(),
                    partition_by=[F("product_id")],
                    order_by=F("price").asc(),
                ),
                total_offers=Subquery(offers_count_sq),
            )
            .filter(rn=1)
            .select_related("product", "shop")
        )

        data = OfferSerializer(best_offers, many=True).data
        return Response(data, status=200)

    @extend_schema(
        summary="Обновить цены товара",
        description="Запускает задачу обновления цен для конкретного товара",
        tags=["products"],
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="refresh",
        permission_classes=[permissions.IsAuthenticated],
    )
    def refresh(self, request, pk=None):
        user_telegram_id = getattr(request.user, "telegram_id", None)
        refresh_product.delay(int(pk), user_telegram_id=user_telegram_id)
        return Response({"queued": True}, status=202)


@extend_schema(tags=["offers"])
class OfferViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = OfferSerializer
    queryset = Offer.objects.all()

    @extend_schema(
        summary="Список предложений",
        description="Получение списка предложений с фильтрацией",
        tags=["offers"],
        parameters=[
            OpenApiParameter(
                name="product",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="ID товара",
            ),
            OpenApiParameter(
                name="shop",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="ID магазина",
            ),
            OpenApiParameter(
                name="is_available",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="Доступность товара",
            ),
            OpenApiParameter(
                name="ordering",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Сортировка (price, last_updated, -price, -last_updated)",
            ),
        ],
    )
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


@extend_schema(tags=["alerts"])
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
    http_method_names = ["get", "post", "delete", "patch"]

    @extend_schema(
        summary="Список уведомлений",
        description="Получение списка уведомлений о ценах для текущего пользователя",
        tags=["alerts"],
    )
    def get_queryset(self):
        return PriceAlert.objects.filter(user=self.request.user).select_related(
            "product", "shop"
        )

    @extend_schema(
        summary="Создать уведомление",
        description="Создание нового уведомления о цене",
        tags=["alerts"],
    )
    def perform_create(self, serializer):
        obj = serializer.save(user=self.request.user, is_active=True)
        check_alerts_for_product.delay(obj.product_id)

    @extend_schema(
        summary="Активировать/деактивировать уведомление",
        description="Переключение статуса уведомления",
        tags=["alerts"],
    )
    @action(detail=True, methods=["post"], url_path="toggle")
    def toggle(self, request, pk=None):
        alert = self.get_object()
        alert.is_active = not alert.is_active
        alert.save(update_fields=["is_active"])
        return Response({"is_active": alert.is_active}, status=200)

    @extend_schema(
        summary="Товары со скидками",
        description="Получение товаров со скидками за последнюю неделю",
        tags=["alerts"],
        parameters=[
            OpenApiParameter(
                name="limit",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Количество товаров (по умолчанию 10)",
            ),
        ],
    )
    @action(detail=False, methods=["get"], url_path="discounts")
    def discounts(self, request):
        week_ago = datetime.now() - timedelta(days=7)

        offers_with_history = Offer.objects.filter(
            price_history__timestamp__gte=week_ago
        ).distinct()

        discounted_offers = []
        for offer in offers_with_history:
            previous_price = (
                PriceHistory.objects.filter(offer=offer).order_by("-timestamp").first()
            )

            if previous_price and offer.price < previous_price.price:
                discount_percentage = (
                    (previous_price.price - offer.price) / previous_price.price
                ) * 100

                offer_data = OfferSerializer(offer).data
                offer_data["discount_percentage"] = discount_percentage
                discounted_offers.append(offer_data)

        discounted_offers.sort(key=lambda x: x["discount_percentage"], reverse=True)

        limit = int(request.query_params.get("limit", 10))
        discounted_offers = discounted_offers[:limit]

        return Response(discounted_offers)


@extend_schema(tags=["shops"])
class ShopViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = ShopSerializer
    queryset = Shop.objects.all()
    http_method_names = ["get"]

    @extend_schema(
        summary="Список активных магазинов",
        description="Получение списка всех активных магазинов",
        tags=["shops"],
    )
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

    @extend_schema(
        summary="Обновить товары магазина",
        description="Запускает задачу обновления всех товаров конкретного магазина",
        tags=["shops"],
    )
    @action(detail=True, methods=["post"], url_path="refresh-products")
    def refresh_products(self, request, pk=None):
        update_shop_products.delay(int(pk))
        return Response({"queued": True}, status=202)

    @extend_schema(
        summary="Найти новые товары",
        description="Запускает задачу поиска новых товаров в магазине",
        tags=["shops"],
        parameters=[
            OpenApiParameter(
                name="limit",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Количество товаров для поиска (по умолчанию 50)",
            ),
        ],
    )
    @action(detail=True, methods=["post"], url_path="discover")
    def discover_products(self, request, pk=None):
        limit = int(request.data.get("limit", 50))
        discover_products_for_shop.delay(int(pk), limit)
        return Response({"queued": True}, status=202)

    @extend_schema(
        summary="Проверить здоровье парсеров",
        description="Запускает задачу проверки работоспособности всех парсеров",
        tags=["health"],
    )
    @action(detail=False, methods=["get"], url_path="health-check")
    def health_check(self, request):
        result = health_check_parsers.delay()
        return Response({"task_id": result.id}, status=202)
