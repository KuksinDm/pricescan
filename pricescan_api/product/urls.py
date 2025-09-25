from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    OfferViewSet,
    PriceAlertViewSet,
    PriceHistoryViewSet,
    ProductViewSet,
    ShopViewSet,
)

router = DefaultRouter()
router.register(r"products", ProductViewSet, basename="product")
router.register(r"offers", OfferViewSet, basename="offer")
router.register(r"price-alerts", PriceAlertViewSet, basename="price-alert")
router.register(r"price-history", PriceHistoryViewSet, basename="price-history")
router.register(r"shops", ShopViewSet, basename="shop")

urlpatterns = [
    path("", include(router.urls)),
]
