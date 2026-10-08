from django.urls import path

from . import views, webhooks

urlpatterns = [
    path("checkout/", views.CheckoutView.as_view(), name="checkout"),
    path(
        "checkout/sessions/<str:session_id>/",
        views.CheckoutSessionView.as_view(),
        name="checkout-session",
    ),
    path("webhooks/stripe/", webhooks.stripe_webhook, name="stripe-webhook"),
]
