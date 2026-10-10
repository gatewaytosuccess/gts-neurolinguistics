from django.urls import path

from . import views, webhooks

urlpatterns = [
    path("checkout/", views.CheckoutView.as_view(), name="checkout"),
    path(
        "checkout/sessions/<str:session_id>/",
        views.CheckoutSessionView.as_view(),
        name="checkout-session",
    ),
    path("users/me/orders/", views.MyOrderListView.as_view(), name="user-me-orders"),
    path(
        "users/me/orders/<uuid:pk>/",
        views.MyOrderDetailView.as_view(),
        name="user-me-order",
    ),
    path("admin/orders/", views.AdminOrderListView.as_view(), name="admin-order-list"),
    path("webhooks/stripe/", webhooks.stripe_webhook, name="stripe-webhook"),
]
