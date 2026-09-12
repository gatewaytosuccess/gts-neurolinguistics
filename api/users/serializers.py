from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """The signed-in user, as the frontend sees them.

    Every field is read-only: Clerk owns this data and the webhook overwrites
    it, so accepting writes here would only produce edits that vanish on the
    next ``user.updated``.

    Deliberately absent: ``status`` (authentication rejects anything that isn't
    ``active``, so it would be a constant), ``suspension_reason`` (an admin
    audit note, not something its subject reads) and the Django staff flags,
    which are about /admin/ rather than about the product.
    """

    class Meta:
        model = User
        fields = ["id", "email", "name", "avatar_url", "role", "created_at"]
        read_only_fields = fields
