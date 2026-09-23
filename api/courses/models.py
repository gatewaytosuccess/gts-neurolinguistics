from django.conf import settings
from django.db import models

from common.models import BaseModel
from enrollments.models import EnrollmentStatus
from reviews.models import ReviewStatus


class CourseStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"


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

    def with_counts(self):
        """Adds ``module_count``, ``lesson_count`` and ``active_enrollment_count``.

        Revoked enrollments are not counted.
        """
        # distinct: the joins fan out, so each count would otherwise multiply the others.
        return self.annotate(
            module_count=models.Count("modules", distinct=True),
            lesson_count=models.Count("modules__lessons", distinct=True),
            active_enrollment_count=models.Count(
                "enrollments",
                filter=models.Q(enrollments__status=EnrollmentStatus.ACTIVE),
                distinct=True,
            ),
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

    class Meta(BaseModel.Meta):
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

    class Meta(BaseModel.Meta):
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
    video_key = models.CharField(max_length=500, blank=True, help_text="Private bucket key.")
    slides_key = models.CharField(max_length=500, blank=True, help_text="Private bucket key.")
    body = models.TextField(blank=True, help_text="Markdown.")
    position = models.PositiveIntegerField()
    is_preview = models.BooleanField(default=False, help_text="Free sample lesson.")
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)

    class Meta(BaseModel.Meta):
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

    @property
    def is_empty(self):
        return not (self.video_key or self.slides_key or self.body)
