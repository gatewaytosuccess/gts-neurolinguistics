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


class AdminUserRoleSerializer(serializers.ModelSerializer):
    """Writes ``role`` and nothing else; any other field sent is ignored.

    Refuses ``instructor``, the requester's own row, and making a user who
    isn't active an admin. Expects ``request`` in the context, and an instance
    locked for update so the status it checks can't change before the save.
    """

    role = serializers.ChoiceField(choices=Role.choices)

    class Meta:
        model = User
        fields = ["role"]

    def validate_role(self, value):
        # The role grants nothing yet.
        if value == Role.INSTRUCTOR:
            raise serializers.ValidationError(
                "Nobody can be made an instructor. Choose learner or admin."
            )
        return value

    def validate(self, attrs):
        user = self.instance
        if user.pk == self.context["request"].user.pk:
            raise serializers.ValidationError("You can't change your own role.")
        if attrs["role"] == Role.ADMIN and not user.is_admin and not user.is_active:
            raise serializers.ValidationError(
                f"Only an active user can be made an admin. This user is {user.status}."
            )
        return attrs

    def update(self, instance, validated_data):
        instance.role = validated_data["role"]
        instance.save(update_fields=["role", "updated_at"])
        return instance


class AdminUserSuspendSerializer(serializers.Serializer):
    """Expects the locked target as ``user`` and the request as ``request`` in its context."""

    reason = serializers.CharField(
        max_length=500,
        error_messages={
            "required": "Give a reason for suspending this user.",
            "blank": "Give a reason for suspending this user.",
        },
    )

    def validate(self, attrs):
        user = self.context["user"]
        if user.pk == self.context["request"].user.pk:
            raise serializers.ValidationError("You can't change your own role or status.")
        if user.is_admin:
            raise serializers.ValidationError("An admin can't be suspended. Demote them first.")
        if user.status == UserStatus.SUSPENDED:
            raise serializers.ValidationError("This user is already suspended.")
        return attrs


class AdminUserReinstateSerializer(serializers.Serializer):
    """Takes no fields. Expects the locked target as ``user`` and the request as ``request``."""

    def validate(self, attrs):
        user = self.context["user"]
        if user.pk == self.context["request"].user.pk:
            raise serializers.ValidationError("You can't change your own role or status.")
        if user.status != UserStatus.SUSPENDED:
            raise serializers.ValidationError("This user isn't suspended.")
        return attrs
