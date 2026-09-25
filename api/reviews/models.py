"""The database does not check that a reviewer is enrolled; callers must."""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from common.models import BaseModel


class ReviewStatus(models.TextChoices):
    PUBLISHED = "published", "Published"
    HIDDEN = "hidden", "Hidden"


class Review(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews"
    )
    course = models.ForeignKey("courses.Course", on_delete=models.PROTECT, related_name="reviews")
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    body = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.PUBLISHED
    )

    class Meta(BaseModel.Meta):
        db_table = "reviews"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "course"], name="unique_review_per_course"),
            models.CheckConstraint(
                condition=models.Q(rating__gte=1, rating__lte=5), name="rating_between_1_and_5"
            ),
        ]

    def __str__(self):
        return f"{self.rating}* {self.course_id}"
