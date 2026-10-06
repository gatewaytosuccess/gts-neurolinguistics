from django.conf import settings
from django.db import models

from common.models import BaseModel, UUIDModel


class EnrollmentSource(models.TextChoices):
    PURCHASE = "purchase", "Purchase"
    MANUAL = "manual", "Manual"
    COMP = "comp", "Comp"


class EnrollmentStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    REVOKED = "revoked", "Revoked"


class ProgressStatus(models.TextChoices):
    NOT_STARTED = "not_started", "Not started"
    IN_PROGRESS = "in_progress", "In progress"
    COMPLETED = "completed", "Completed"


class EnrollmentQuerySet(models.QuerySet):
    def with_progress(self):
        """Adds ``lesson_count``, ``completed_lesson_count`` and ``last_activity_at``.

        All three read only the course's current lessons and the enrolled
        user's own progress. ``last_activity_at`` is ``None`` with no progress.
        """
        lessons = "course__modules__lessons"
        own = models.Q(course__modules__lessons__progress__user=models.F("user"))
        completed = own & models.Q(
            course__modules__lessons__progress__status=ProgressStatus.COMPLETED
        )
        # distinct: the progress join fans each lesson out to every learner's row.
        return self.annotate(
            lesson_count=models.Count(lessons, distinct=True),
            completed_lesson_count=models.Count(lessons, filter=completed, distinct=True),
            last_activity_at=models.Max(
                "course__modules__lessons__progress__updated_at", filter=own
            ),
        )


class Enrollment(UUIDModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments"
    )
    course = models.ForeignKey(
        "courses.Course", on_delete=models.PROTECT, related_name="enrollments"
    )
    source = models.CharField(max_length=20, choices=EnrollmentSource.choices)
    order = models.ForeignKey(
        "commerce.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="enrollments",
        help_text="Set when source = purchase.",
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20, choices=EnrollmentStatus.choices, default=EnrollmentStatus.ACTIVE
    )
    revoked_at = models.DateTimeField(null=True, blank=True)

    objects = EnrollmentQuerySet.as_manager()

    class Meta(UUIDModel.Meta):
        db_table = "enrollments"
        ordering = ["-enrolled_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "course"], name="unique_enrollment_per_course")
        ]

    def __str__(self):
        return f"{self.user_id} -> {self.course_id}"


class LessonProgress(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lesson_progress"
    )
    lesson = models.ForeignKey("courses.Lesson", on_delete=models.CASCADE, related_name="progress")
    status = models.CharField(
        max_length=20, choices=ProgressStatus.choices, default=ProgressStatus.NOT_STARTED
    )
    last_position_seconds = models.PositiveIntegerField(default=0, help_text="Video resume point.")
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        db_table = "lesson_progress"
        verbose_name_plural = "lesson progress"
        constraints = [
            models.UniqueConstraint(fields=["user", "lesson"], name="unique_progress_per_lesson")
        ]

    def __str__(self):
        return f"{self.user_id} / {self.lesson_id}: {self.status}"
