from django.contrib import admin

from .models import Course, Lesson, Module


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0
    fields = ("position", "title", "content_type", "is_preview", "duration_seconds")


class ModuleInline(admin.TabularInline):
    model = Module
    extra = 0
    fields = ("position", "title")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "price_cents", "instructor", "created_at")
    list_filter = ("status",)
    search_fields = ("title", "slug", "description")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ModuleInline]


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "position")
    list_filter = ("course",)
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "module", "position", "content_type", "is_preview")
    list_filter = ("content_type", "is_preview")
    search_fields = ("title",)
