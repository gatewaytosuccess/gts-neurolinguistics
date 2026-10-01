from django.urls import path

from . import views, webhooks

urlpatterns = [
    path("users/me/", views.me, name="user-me"),
    path("admin/users/", views.AdminUserListView.as_view(), name="admin-user-list"),
    path("admin/users/<uuid:pk>/", views.AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("webhooks/clerk/", webhooks.clerk_webhook, name="clerk-webhook"),
]
