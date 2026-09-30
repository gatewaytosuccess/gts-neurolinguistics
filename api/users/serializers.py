from rest_framework import serializers

from commerce.models import Order, OrderItem
from courses.models import Course
from reviews.models import Review

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


class AdminUserOrderItemSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["title", "unit_price_cents"]
        read_only_fields = fields


class AdminUserOrderSerializer(serializers.ModelSerializer):
    items = AdminUserOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ["id", "created_at", "status", "total_cents", "items"]
        read_only_fields = fields


class AdminUserReviewCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ["id", "title", "slug", "status"]
        read_only_fields = fields


class AdminUserReviewSerializer(serializers.ModelSerializer):
    course = AdminUserReviewCourseSerializer(read_only=True)

    class Meta:
        model = Review
        fields = ["id", "rating", "body", "status", "created_at", "course"]
        read_only_fields = fields


class AdminUserDetailSerializer(serializers.ModelSerializer):
    """Hidden reviews and draft courses included. The Clerk id itself is never exposed."""

    has_clerk_identity = serializers.SerializerMethodField()
    orders = AdminUserOrderSerializer(many=True, read_only=True)
    reviews = AdminUserReviewSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "avatar_url",
            "role",
            "status",
            "suspended_at",
            "suspension_reason",
            "created_at",
            "has_clerk_identity",
            "orders",
            "reviews",
        ]
        read_only_fields = fields

    def get_has_clerk_identity(self, user):
        return bool(user.clerk_user_id)
