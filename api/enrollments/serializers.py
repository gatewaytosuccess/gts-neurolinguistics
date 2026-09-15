from rest_framework import serializers

from .models import Enrollment


class EnrollmentSerializer(serializers.ModelSerializer):
    """Expects ``course`` to be select-related."""

    course_id = serializers.UUIDField(read_only=True)
    course_slug = serializers.SlugField(source="course.slug", read_only=True)

    class Meta:
        model = Enrollment
        fields = ["id", "course_id", "course_slug", "source", "enrolled_at"]
        read_only_fields = fields
