from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Role ``admin`` only; instructors are refused.

    An unauthenticated request gets 401, not 403. Suspended and banned accounts
    never reach this check: authentication rejects them first.
    """

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_admin)
