from django.conf import settings
from rest_framework.permissions import BasePermission


class IsServiceCall(BasePermission):
    def has_permission(self, request, view):
        expected = getattr(settings, "BOT_SERVICE_TOKEN", "") or ""
        provided = request.headers.get("X-Service-Token", "") or ""
        return bool(expected) and provided == expected
