import logging
from datetime import timezone

from django.contrib.auth import get_user_model
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.tokens import RefreshToken

from .models import UserFavorite
from .permissions import IsServiceCall
from .serializers import (
    BotAuthRequestSerializer,
    TokenPairSerializer,
    UserFavoriteSerializer,
    UserProfileSerializer,
)

User = get_user_model()

logger = logging.getLogger("user")


class UserViewSet(GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProfileSerializer

    @extend_schema(
        responses={200: UserProfileSerializer},
        summary="Получить профиль пользователя",
        tags=["users"],
    )
    @action(
        detail=False,
        methods=["GET", "PATCH", "DELETE"],
    )
    def me(self, request):
        if request.method == "GET":
            serializer = UserProfileSerializer(request.user)
            return Response(serializer.data, status=status.HTTP_200_OK)

        if request.method == "PATCH":
            serializer = UserProfileSerializer(
                request.user, data=request.data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        if request.method == "DELETE":
            user = request.user
            user.is_deleted = True
            user.deleted_at = timezone.now()
            user.is_active = False
            user.save()
            return Response(
                {"detail": "Пользователь удалён."}, status=status.HTTP_204_NO_CONTENT
            )


class UserFavoriteViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserFavoriteSerializer
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        return UserFavorite.objects.filter(user=self.request.user).select_related(
            "product"
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# class SearchHistoryViewSet(
#     mixins.ListModelMixin,
#     mixins.CreateModelMixin,
#     mixins.DestroyModelMixin,
#     GenericViewSet,
# ):
#     permission_classes = [permissions.IsAuthenticated]
#     serializer_class = SearchHistorySerializer
#     http_method_names = ["get", "post", "delete"]

#     def get_queryset(self):
#         return SearchHistory.objects.filter(user=self.request.user)

#     def perform_create(self, serializer):
#         serializer.save(user=self.request.user)

#     @extend_schema(
#         summary="Очистить всю историю поиска",
#         description="Удаляет все записи истории текущего пользователя "
#         "и возвращает количество удалённых.",
#         tags=["search-history"],
#     )
#     @action(detail=False, methods=["delete"], url_path="clear")
#     def clear(self, request):
#         deleted = self.get_queryset().delete()[0]
#         return Response({"deleted": deleted}, status=status.HTTP_200_OK)


class BotJWTView(APIView):
    permission_classes = [IsServiceCall]
    authentication_classes = []

    @extend_schema(
        auth=[{"ServiceToken": []}],
        summary="Выдать JWT по Telegram ID (вызов от бота)",
        tags=["auth"],
        request=BotAuthRequestSerializer,
        responses={200: TokenPairSerializer},
        parameters=[
            OpenApiParameter(
                name="X-Service-Token",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.HEADER,
                required=True,
                description="Сервисный токен бота",
            ),
        ],
    )
    def post(self, request):
        serializer = BotAuthRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        telegram_id = data["telegram_id"]
        defaults = {
            "username": f"tg_{telegram_id}",
            "first_name": data.get("first_name", ""),
            "last_name": data.get("last_name", ""),
            "telegram_username": data.get("telegram_username"),
            "language_code": data.get("language_code"),
        }

        user, created = User.objects.get_or_create(
            telegram_id=telegram_id, defaults=defaults
        )
        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])
        else:
            to_update = []
            for data_key in (
                "first_name",
                "last_name",
                "telegram_username",
                "language_code",
            ):
                if data_key in data and getattr(user, data_key) != data.get(data_key):
                    setattr(user, data_key, data.get(data_key))
                    to_update.append(data_key)
            if to_update:
                user.save(update_fields=to_update)

        refresh = RefreshToken.for_user(user)
        response = TokenPairSerializer(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
        ).data
        return Response(response, status=200)
