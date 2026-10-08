from django.utils.text import slugify
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from common import storage

from . import lesson_files, thumbnails
from .models import Course, Lesson, Module


class PublicUrlField(serializers.ReadOnlyField):
    """An object key as its CloudFront URL; blank stays blank."""

    def to_representation(self, value):
        return storage.public_url(value)


class PresignedDownloadField(serializers.ReadOnlyField):
    """A private bucket key as a presigned GET URL; blank stays blank. Admin serializers only."""

    def to_representation(self, value):
        return lesson_files.download_url(value)


class CourseListSerializer(serializers.ModelSerializer):
    """Expects a queryset annotated by ``Course.objects.with_ratings()``."""

    thumbnail_url = PublicUrlField(source="thumbnail_key")
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


class PublicLessonSerializer(serializers.ModelSerializer):
    """Expects lessons annotated with ``has_body``.

    ``kinds`` lists which of ``video``, ``slides`` and ``text`` the lesson has, in
    that order. Never carries object keys, URLs or the body.
    """

    kinds = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = ["id", "title", "position", "duration_seconds", "is_preview", "kinds"]
        read_only_fields = fields

    def get_kinds(self, lesson):
        present = {"video": lesson.video_key, "slides": lesson.slides_key, "text": lesson.has_body}
        return [kind for kind, has_it in present.items() if has_it]


class PublicModuleSerializer(serializers.ModelSerializer):
    """Expects lessons prefetched the way ``PublicLessonSerializer`` expects them."""

    lesson_count = serializers.SerializerMethodField()
    lessons = PublicLessonSerializer(many=True, read_only=True)

    class Meta:
        model = Module
        fields = ["id", "title", "position", "lesson_count", "lessons"]
        read_only_fields = fields

    def get_lesson_count(self, module):
        return len(module.lessons.all())


class CourseDetailSerializer(CourseListSerializer):
    """A catalog course with its curriculum.

    Expects a queryset annotated by ``Course.objects.with_ratings()``, with modules
    and lessons prefetched in order the way ``PublicModuleSerializer`` expects them.
    ``duration_seconds`` sums the lessons that have one, and is null when none do.
    """

    module_count = serializers.SerializerMethodField()
    lesson_count = serializers.SerializerMethodField()
    preview_lesson_count = serializers.SerializerMethodField()
    duration_seconds = serializers.SerializerMethodField()
    modules = PublicModuleSerializer(many=True, read_only=True)

    class Meta(CourseListSerializer.Meta):
        fields = CourseListSerializer.Meta.fields + [
            "module_count",
            "lesson_count",
            "preview_lesson_count",
            "duration_seconds",
            "modules",
        ]
        read_only_fields = fields

    @staticmethod
    def _lessons(course):
        return [lesson for module in course.modules.all() for lesson in module.lessons.all()]

    def get_module_count(self, course):
        return len(course.modules.all())

    def get_lesson_count(self, course):
        return len(self._lessons(course))

    def get_preview_lesson_count(self, course):
        return sum(1 for lesson in self._lessons(course) if lesson.is_preview)

    def get_duration_seconds(self, course):
        known = [
            lesson.duration_seconds
            for lesson in self._lessons(course)
            if lesson.duration_seconds is not None
        ]
        return sum(known) if known else None


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


def unique_slug(title, exclude=None):
    """``title`` slugified, with ``-2``, ``-3``… appended until no other course uses it.

    Falls back to ``course`` when nothing in the title survives slugifying.
    """
    max_length = Course._meta.get_field("slug").max_length
    base = slugify(title)[:max_length].strip("-") or "course"
    others = Course.objects.exclude(pk=exclude.pk) if exclude else Course.objects.all()

    candidate, n = base, 1
    while others.filter(slug=candidate).exists():
        n += 1
        suffix = f"-{n}"
        candidate = base[: max_length - len(suffix)].rstrip("-") + suffix
    return candidate


class AdminCourseSerializer(serializers.ModelSerializer):
    """Creates and edits a course's details.

    A blank or missing ``slug`` on create, or a blank one on a draft's update, is
    generated from the title. ``status`` is read-only: a create is always a draft.

    ``thumbnail_key`` can only be set on an update, to a blank (removing it) or an
    uploaded object under the course's prefix. Deleting the replaced object is left
    to the caller, as is keeping a published course publishable.
    """

    slug = serializers.SlugField(
        max_length=255,
        required=False,
        allow_blank=True,
        validators=[
            UniqueValidator(
                queryset=Course.objects.all(), message="Another course already uses this slug."
            )
        ],
    )
    thumbnail_url = PublicUrlField(source="thumbnail_key")

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "price_cents",
            "thumbnail_key",
            "thumbnail_url",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]
        extra_kwargs = {
            "price_cents": {
                # Stripe's minimum charge in USD.
                "min_value": 50,
                "error_messages": {"min_value": "The price must be at least $0.50."},
            },
        }

    def validate_thumbnail_key(self, value):
        course = self.instance
        if not value:
            return value
        if course is None:
            raise serializers.ValidationError("Add a thumbnail once the course is created.")
        if value == course.thumbnail_key:
            return value
        if not value.startswith(thumbnails.key_prefix(course)):
            raise serializers.ValidationError("This isn't an upload for this course.")
        if not thumbnails.exists(value):
            raise serializers.ValidationError("The upload didn't finish. Upload the file again.")
        return value

    def validate(self, attrs):
        course = self.instance

        # A published course's URL is public.
        if course is not None and course.is_published:
            if "slug" in attrs and attrs["slug"] != course.slug:
                raise serializers.ValidationError(
                    {"slug": "The slug can't change while the course is published."}
                )

        if not attrs.get("slug") and (course is None or "slug" in attrs):
            title = attrs["title"] if "title" in attrs else course.title
            attrs["slug"] = unique_slug(title, exclude=course)

        return attrs


class ThumbnailUploadSerializer(serializers.Serializer):
    content_type = serializers.ChoiceField(
        choices=list(thumbnails.TYPES),
        error_messages={"invalid_choice": "Choose a JPEG, PNG or WebP image."},
    )


class AdminCurriculumLessonSerializer(serializers.ModelSerializer):
    """Expects lessons annotated with ``learners_with_progress``."""

    learners_with_progress = serializers.IntegerField(read_only=True)

    class Meta:
        model = Lesson
        fields = ["id", "title", "position", "is_empty", "is_preview", "learners_with_progress"]
        read_only_fields = fields


class AdminCurriculumModuleSerializer(serializers.ModelSerializer):
    """Expects modules annotated with ``learners_with_progress`` and lessons prefetched
    the way ``AdminCurriculumLessonSerializer`` expects them."""

    learners_with_progress = serializers.IntegerField(read_only=True)
    lessons = AdminCurriculumLessonSerializer(many=True, read_only=True)

    class Meta:
        model = Module
        fields = ["id", "title", "position", "learners_with_progress", "lessons"]
        read_only_fields = fields


class AdminModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ["id", "title", "position"]
        read_only_fields = ["id", "position"]


class AdminLessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ["id", "module", "title", "position", "is_empty", "is_preview"]
        read_only_fields = ["id", "module", "position", "is_empty", "is_preview"]


class LessonModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ["id", "title", "position"]
        read_only_fields = fields


class LessonCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ["id", "title", "slug", "status"]
        read_only_fields = fields


class AdminLessonDetailSerializer(serializers.ModelSerializer):
    """Everything about a lesson, with its module and course.

    ``duration_seconds`` is positive or null. ``video_key`` and ``slides_key`` can
    be set to a blank (removing the file) or an uploaded object of that kind under
    the lesson's prefix. Deleting the replaced object is left to the caller, as is
    keeping a published course publishable. ``video_url`` and ``slides_url`` expire
    after an hour.
    """

    module = LessonModuleSerializer(read_only=True)
    course = LessonCourseSerializer(source="module.course", read_only=True)
    video_url = PresignedDownloadField(source="video_key")
    slides_url = PresignedDownloadField(source="slides_key")

    class Meta:
        model = Lesson
        fields = [
            "id",
            "title",
            "body",
            "is_preview",
            "duration_seconds",
            "video_key",
            "video_url",
            "slides_key",
            "slides_url",
            "position",
            "is_empty",
            "module",
            "course",
        ]
        read_only_fields = ["id", "position", "is_empty", "module", "course"]
        extra_kwargs = {
            "duration_seconds": {
                "min_value": 1,
                "error_messages": {"min_value": "The duration must be greater than 0."},
            },
        }

    def _validate_file_key(self, kind, value):
        lesson = self.instance
        if not value or value == getattr(lesson, lesson_files.KINDS[kind].field):
            return value
        if not lesson_files.is_upload_for(lesson, kind, value):
            raise serializers.ValidationError(f"This isn't a {kind} upload for this lesson.")
        if not lesson_files.exists(value):
            raise serializers.ValidationError("The upload didn't finish. Upload the file again.")
        return value

    def validate_video_key(self, value):
        return self._validate_file_key("video", value)

    def validate_slides_key(self, value):
        return self._validate_file_key("slides", value)


class LessonUploadSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(
        choices=list(lesson_files.KINDS),
        error_messages={"invalid_choice": "Choose video or slides."},
    )


class MoveModuleSerializer(serializers.Serializer):
    """Out-of-range positions are clamped, not refused."""

    position = serializers.IntegerField()


class MoveLessonSerializer(serializers.Serializer):
    """Out-of-range positions are clamped, not refused.

    ``position`` may be left out only with a ``module_id``, and then means last.
    ``module_id`` must name a module of the lesson's course; it validates to that
    ``Module``. Expects the lesson as ``context["lesson"]``.
    """

    position = serializers.IntegerField(required=False)
    module_id = serializers.UUIDField(required=False)

    def validate_module_id(self, value):
        course_id = self.context["lesson"].module.course_id
        module = Module.objects.filter(pk=value, course_id=course_id).first()
        if module is None:
            raise serializers.ValidationError("Choose a module of this lesson's course.")
        return module

    def validate(self, attrs):
        if "position" not in attrs and "module_id" not in attrs:
            raise serializers.ValidationError({"position": "This field is required."})
        return attrs
