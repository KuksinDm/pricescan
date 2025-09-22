from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AlertRuleViewSet,
    AlertTriggerViewSet,
    MetricViewSet,
    PerformanceLogViewSet,
    SystemHealthViewSet,
    SystemOverviewViewSet,
)

router = DefaultRouter()
router.register(r"metrics", MetricViewSet, basename="metric")
router.register(r"health", SystemHealthViewSet, basename="health")
router.register(r"alert-rules", AlertRuleViewSet, basename="alert-rule")
router.register(r"alert-triggers", AlertTriggerViewSet, basename="alert-trigger")
router.register(r"performance-logs", PerformanceLogViewSet, basename="performance-log")
router.register(r"overview", SystemOverviewViewSet, basename="overview")

urlpatterns = [
    path("", include(router.urls)),
]
