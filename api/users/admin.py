from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "name", "role", "status", "created_at")
    list_filter = ("role", "status", "is_staff", "is_superuser")
    search_fields = ("email", "name", "clerk_user_id")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at", "last_login")
    fieldsets = (
        (None, {"fields": ("id", "email", "password", "clerk_user_id")}),
        ("Profile", {"fields": ("name", "avatar_url")}),
        ("Access", {"fields": ("role", "status", "suspended_at", "suspension_reason")}),
        ("Permissions", {"fields": ("is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (
            None,
            {"classes": ("wide",), "fields": ("email", "name", "role", "password1", "password2")},
        ),
    )
