from django.contrib import admin

from .models import Cart, CartItem, Coupon, Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    raw_id_fields = ("course",)


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    raw_id_fields = ("course",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "total_cents", "created_at")
    list_filter = ("status",)
    search_fields = ("id", "user__email", "payment_ref")
    raw_id_fields = ("user", "coupon")
    inlines = [OrderItemInline]


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "updated_at")
    raw_id_fields = ("user",)
    inlines = [CartItemInline]


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_type", "discount_value", "status", "times_redeemed", "expires_at")
    list_filter = ("discount_type", "status")
    search_fields = ("code", "description")
