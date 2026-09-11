from django.contrib import admin

from .models import Enrollment, LessonProgress


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "source", "status", "enrolled_at")
    list_filter = ("source", "status")
    search_fields = ("user__email", "course__title")
    raw_id_fields = ("user", "course", "order")


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "lesson", "status", "last_position_seconds", "completed_at")
    list_filter = ("status",)
    search_fields = ("user__email", "lesson__title")
    raw_id_fields = ("user", "lesson")
