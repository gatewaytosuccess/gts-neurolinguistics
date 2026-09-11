from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("course", "user", "rating", "status", "created_at")
    list_filter = ("rating", "status")
    search_fields = ("course__title", "user__email", "body")
    raw_id_fields = ("user", "course")
