from rest_framework import serializers

from users.models import User

from .models import Order, OrderItem, OrderStatus


class OrderItemSerializer(serializers.ModelSerializer):
    course_slug = serializers.CharField(source="course.slug", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["course_slug", "course_title", "unit_price_cents"]
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ["id", "created_at", "status", "total_cents", "items"]
        read_only_fields = fields


class OrderReceiptSerializer(OrderSerializer):
    class Meta(OrderSerializer.Meta):
        fields = [
            *OrderSerializer.Meta.fields,
            "subtotal_cents",
            "discount_cents",
            "receipt_url",
        ]
        read_only_fields = fields


class AdminOrderFiltersSerializer(serializers.Serializer):
    """The order list's ``status`` query parameter; blank means no filter."""

    status = serializers.ChoiceField(choices=OrderStatus.choices, required=False, allow_blank=True)


class AdminOrderBuyerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "email"]
        read_only_fields = fields


class AdminOrderListItemSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["title"]
        read_only_fields = fields


class AdminOrderListSerializer(serializers.ModelSerializer):
    buyer = AdminOrderBuyerSerializer(source="user", read_only=True)
    items = AdminOrderListItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ["id", "created_at", "status", "total_cents", "buyer", "items"]
        read_only_fields = fields
