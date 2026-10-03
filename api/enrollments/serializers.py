from rest_framework import serializers

from courses import lesson_files
from courses.models import Course, Lesson, Module
from courses.serializers import PublicLessonSerializer

from .access import is_locked
from .models import Enrollment, EnrollmentSource, EnrollmentStatus


class EnrollmentSerializer(serializers.ModelSerializer):
    """Expects ``course`` to be select-related."""

    course_id = serializers.UUIDField(read_only=True)
    course_slug = serializers.SlugField(source="course.slug", read_only=True)

    class Meta:
        model = Enrollment
        fields = ["id", "course_id", "course_slug", "source", "enrolled_at"]
        read_only_fields = fields


class AdminEnrollmentCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ["id", "title", "slug", "status"]
        read_only_fields = fields


class AdminEnrollmentSerializer(serializers.ModelSerializer):
    """Expects ``course`` select-related and the ``with_progress`` annotations."""

    course = AdminEnrollmentCourseSerializer(read_only=True)
    order_id = serializers.UUIDField(read_only=True)
    completed_lesson_count = serializers.IntegerField(read_only=True)
    lesson_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            "id",
            "course",
            "source",
            "status",
            "order_id",
            "enrolled_at",
            "revoked_at",
            "completed_lesson_count",
            "lesson_count",
        ]
        read_only_fields = fields


class AdminEnrollmentGrantSerializer(serializers.Serializer):
    """Drafts can be granted. Expects the locked target as ``user`` in its context."""

    course_id = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.all(),
        source="course",
        error_messages={"does_not_exist": "No course has this id."},
    )
    source = serializers.ChoiceField(
        choices=[EnrollmentSource.MANUAL, EnrollmentSource.COMP],
        error_messages={"invalid_choice": "Choose manual or comp."},
    )

    def validate(self, attrs):
        existing = Enrollment.objects.filter(user=self.context["user"], course=attrs["course"])
        if existing.filter(status=EnrollmentStatus.ACTIVE).exists():
            raise serializers.ValidationError("This user is already enrolled in this course.")
        if existing.exists():
            raise serializers.ValidationError(
                "This user's enrollment in this course was revoked. "
                "Restore the existing enrollment instead."
            )
        return attrs


class ViewerCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ["id", "title", "slug"]
        read_only_fields = fields


class OutlineLessonSerializer(PublicLessonSerializer):
    """Expects ``access`` and ``completed_ids`` in its context.

    ``completed_ids`` must hold only the requester's own completed lessons.
    """

    locked = serializers.SerializerMethodField()
    completed = serializers.SerializerMethodField()

    class Meta(PublicLessonSerializer.Meta):
        fields = ["id", "title", "duration_seconds", "is_preview", "kinds", "locked", "completed"]
        read_only_fields = fields

    def get_locked(self, lesson):
        return is_locked(lesson, self.context["access"])

    def get_completed(self, lesson):
        return lesson.pk in self.context["completed_ids"]


class OutlineModuleSerializer(serializers.ModelSerializer):
    """Expects lessons prefetched the way ``PublicLessonSerializer`` expects them."""

    lessons = OutlineLessonSerializer(many=True, read_only=True)

    class Meta:
        model = Module
        fields = ["id", "title", "position", "lessons"]
        read_only_fields = fields


class ViewerLessonSerializer(serializers.ModelSerializer):
    """Expects ``module__course`` select-related.

    Signs the video and slides URLs, so only serialize a lesson the requester may open.
    """

    module = serializers.SerializerMethodField()
    course = ViewerCourseSerializer(source="module.course", read_only=True)
    video_url = serializers.SerializerMethodField()
    slides_url = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = ["id", "title", "module", "course", "body", "video_url", "slides_url"]
        read_only_fields = fields

    def get_module(self, lesson):
        return {"title": lesson.module.title, "position": lesson.module.position}

    def get_video_url(self, lesson):
        return lesson_files.download_url(
            lesson.video_key, lesson_files.VIEWER_DOWNLOAD_EXPIRES_SECONDS
        )

    def get_slides_url(self, lesson):
        return lesson_files.download_url(
            lesson.slides_key, lesson_files.VIEWER_DOWNLOAD_EXPIRES_SECONDS
        )
