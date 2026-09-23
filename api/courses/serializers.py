from django.utils.text import slugify
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

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

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "price_cents",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]
        extra_kwargs = {
            "price_cents": {
                "min_value": 1,
                "error_messages": {"min_value": "The price must be greater than 0."},
            },
        }

    def validate(self, attrs):
        course = self.instance

        # A published course must stay publishable, and its URL is public.
        if course is not None and course.is_published:
            if "slug" in attrs and attrs["slug"] != course.slug:
                raise serializers.ValidationError(
                    {"slug": "The slug can't change while the course is published."}
                )
            if "description" in attrs and not attrs["description"]:
                raise serializers.ValidationError(
                    {"description": "A published course needs a description."}
                )

        if not attrs.get("slug") and (course is None or "slug" in attrs):
            title = attrs["title"] if "title" in attrs else course.title
            attrs["slug"] = unique_slug(title, exclude=course)

        return attrs
