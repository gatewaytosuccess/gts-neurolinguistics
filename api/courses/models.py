from django.conf import settings
from django.db import models

from common.models import BaseModel
from reviews.models import ReviewStatus


class CourseStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"


class ContentType(models.TextChoices):
    VIDEO = "video", "Video"
    SLIDES = "slides", "Slides"
    TEXT = "text", "Text"


class CourseQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=CourseStatus.PUBLISHED)

    def with_ratings(self):
        """Adds ``rating_average`` (``None`` with no reviews) and ``rating_count``.

        Hidden reviews are not counted.
        """
        published_reviews = models.Q(reviews__status=ReviewStatus.PUBLISHED)
        return self.annotate(
            rating_average=models.Avg("reviews__rating", filter=published_reviews),
            rating_count=models.Count("reviews", filter=published_reviews),
        )


class Course(BaseModel):
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses",
        help_text="Null means a platform-owned course.",
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    price_cents = models.PositiveIntegerField()
    thumbnail_url = models.URLField(max_length=500, blank=True)
    status = models.CharField(
        max_length=20, choices=CourseStatus.choices, default=CourseStatus.DRAFT
    )

    objects = CourseQuerySet.as_manager()

    class Meta:
        db_table = "courses"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def is_published(self):
        return self.status == CourseStatus.PUBLISHED


class Module(BaseModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(max_length=255)
    position = models.PositiveIntegerField()

    class Meta:
        db_table = "modules"
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "position"],
                name="unique_module_position_per_course",
                deferrable=models.Deferrable.DEFERRED,
            )
        ]

    def __str__(self):
        return f"{self.course.title} / {self.title}"


class Lesson(BaseModel):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=255)
    content_type = models.CharField(max_length=20, choices=ContentType.choices)
    content_url = models.URLField(
        max_length=500, blank=True, help_text="S3 asset: video or slides."
    )
    content_body = models.TextField(blank=True, help_text="Rich text lessons.")
    position = models.PositiveIntegerField()
    is_preview = models.BooleanField(default=False, help_text="Free sample lesson.")
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = "lessons"
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["module", "position"],
                name="unique_lesson_position_per_module",
                deferrable=models.Deferrable.DEFERRED,
            )
        ]

    def __str__(self):
        return self.title
