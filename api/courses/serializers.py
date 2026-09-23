from rest_framework import serializers

from .models import Course


class CourseListSerializer(serializers.ModelSerializer):
    """Expects a queryset annotated by ``Course.objects.with_ratings()``."""

    rating_average = serializers.FloatField(allow_null=True, read_only=True)
    rating_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Course
        fields = [
            "id",
            "slug",
            "title",
            "description",
            "price_cents",
            "thumbnail_url",
            "rating_average",
            "rating_count",
        ]
        read_only_fields = fields


class AdminCourseListSerializer(serializers.ModelSerializer):
    """Expects a queryset annotated by ``Course.objects.with_counts()``."""

    module_count = serializers.IntegerField(read_only=True)
    lesson_count = serializers.IntegerField(read_only=True)
    active_enrollment_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "slug",
            "status",
            "price_cents",
            "module_count",
            "lesson_count",
            "active_enrollment_count",
            "updated_at",
        ]
        read_only_fields = fields
