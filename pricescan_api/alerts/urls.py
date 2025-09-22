from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AlertHistoryViewSet, AlertViewSet

router = DefaultRouter()
router.register(r"alerts", AlertViewSet, basename="alert")
router.register(r"alert-history", AlertHistoryViewSet, basename="alert-history")

urlpatterns = [
    path("", include(router.urls)),
]
