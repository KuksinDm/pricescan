from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BotJWTView, UserFavoriteViewSet, UserViewSet

app_name = "user"
router = DefaultRouter()
router.register(r"user", UserViewSet, basename="user")
router.register(r"favorites", UserFavoriteViewSet, basename="favorites")
# router.register(r"search-history", SearchHistoryViewSet, basename="search-history")


urlpatterns = [
    path("", include(router.urls)),
    path("auth/jwt/by-telegram/", BotJWTView.as_view(), name="jwt_by_telegram"),
]
