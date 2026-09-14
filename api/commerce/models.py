"""All money is integer cents in a single currency."""

from django.conf import settings
from django.db import models

from common.models import BaseModel, UUIDModel


class OrderStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PAID = "paid", "Paid"
    REFUNDED = "refunded", "Refunded"
    FAILED = "failed", "Failed"


class DiscountType(models.TextChoices):
    PERCENT = "percent", "Percent"
    FIXED = "fixed", "Fixed"


class CouponStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    DISABLED = "disabled", "Disabled"


class Coupon(BaseModel):
    code = models.CharField(max_length=64, unique=True)
    description = models.CharField(max_length=255, blank=True)
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices)
    discount_value = models.PositiveIntegerField(
        help_text="percent: whole percent 1-100. fixed: amount in cents."
    )
    min_subtotal_cents = models.PositiveIntegerField(
        null=True, blank=True, help_text="Minimum order subtotal to qualify."
    )
    max_redemptions = models.PositiveIntegerField(
        null=True, blank=True, help_text="Null = unlimited."
    )
    times_redeemed = models.PositiveIntegerField(default=0)
    starts_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=CouponStatus.choices, default=CouponStatus.ACTIVE
    )

    class Meta:
        db_table = "coupons"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(discount_type="fixed")
                | models.Q(discount_value__gte=1, discount_value__lte=100),
                name="percent_discount_between_1_and_100",
            )
        ]

    def __str__(self):
        return self.code


class Order(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders"
    )
    coupon = models.ForeignKey(
        Coupon, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )
    status = models.CharField(max_length=20, choices=OrderStatus.choices)
    subtotal_cents = models.PositiveIntegerField()
    discount_cents = models.PositiveIntegerField(
        default=0, help_text="Snapshot of the discount actually applied."
    )
    total_cents = models.PositiveIntegerField()
    payment_ref = models.CharField(max_length=255, blank=True, help_text="Provider transaction id.")

    class Meta:
        db_table = "orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order {self.id} ({self.status})"


class OrderItem(UUIDModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    course = models.ForeignKey(
        "courses.Course", on_delete=models.PROTECT, related_name="order_items"
    )
    unit_price_cents = models.PositiveIntegerField(help_text="Price snapshot at purchase.")

    class Meta:
        db_table = "order_items"
        constraints = [
            models.UniqueConstraint(fields=["order", "course"], name="unique_course_per_order")
        ]


class Cart(UUIDModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(
        auto_now=True, help_text="Staleness signal for abandoned-cart email."
    )

    class Meta:
        db_table = "carts"

    def __str__(self):
        return f"Cart {self.id}"


class CartItem(UUIDModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    course = models.ForeignKey(
        "courses.Course", on_delete=models.CASCADE, related_name="cart_items"
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cart_items"
        ordering = ["added_at"]
        constraints = [
            models.UniqueConstraint(fields=["cart", "course"], name="unique_course_per_cart")
        ]
