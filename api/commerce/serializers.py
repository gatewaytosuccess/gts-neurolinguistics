from rest_framework import serializers

from .models import Order, OrderItem


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
