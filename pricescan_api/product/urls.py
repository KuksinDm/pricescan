from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import OfferViewSet, PriceAlertViewSet, ProductViewSet

app_name = "product"
router = DefaultRouter()
router.register(r"products", ProductViewSet, basename="product")
router.register(r"offers", OfferViewSet, basename="offer")
router.register(r"alerts", PriceAlertViewSet, basename="alert")


urlpatterns = [
    path("", include(router.urls)),
]
