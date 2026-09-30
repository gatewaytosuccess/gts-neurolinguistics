from rest_framework import serializers

from .models import Role, User, UserStatus


class UserSerializer(serializers.ModelSerializer):
    """Read-only: ``user.updated`` from Clerk overwrites these fields.

    Deliberately excluded: ``status`` (always ``active`` for an authenticated
    user), ``suspension_reason`` (admin-only) and the Django staff flags.
    """

    class Meta:
        model = User
        fields = ["id", "email", "name", "avatar_url", "role", "created_at"]
        read_only_fields = fields


class AdminUserListSerializer(serializers.ModelSerializer):
    """Expects a queryset annotated with ``active_enrollment_count``."""

    active_enrollment_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "avatar_url",
            "role",
            "status",
            "active_enrollment_count",
            "created_at",
        ]
        read_only_fields = fields


class AdminUserFiltersSerializer(serializers.Serializer):
    """The user list's ``role`` and ``status`` query parameters; blank means no filter."""

    role = serializers.ChoiceField(choices=Role.choices, required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=UserStatus.choices, required=False, allow_blank=True)
