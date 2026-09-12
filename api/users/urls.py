from django.urls import path

from . import views, webhooks

urlpatterns = [
    path("users/me/", views.me, name="user-me"),
    path("webhooks/clerk/", webhooks.clerk_webhook, name="clerk-webhook"),
]
