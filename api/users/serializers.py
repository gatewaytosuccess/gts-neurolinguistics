from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Read-only: ``user.updated`` from Clerk overwrites these fields.

    Deliberately excluded: ``status`` (always ``active`` for an authenticated
    user), ``suspension_reason`` (admin-only) and the Django staff flags.
    """

    class Meta:
        model = User
        fields = ["id", "email", "name", "avatar_url", "role", "created_at"]
        read_only_fields = fields
