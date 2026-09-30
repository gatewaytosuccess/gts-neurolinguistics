from rest_framework import serializers

from .models import Review


def author_name(name):
    """First name and last initial ("Maria G."); a one-word name as-is; blank for blank."""
    words = name.split()
    if len(words) < 2:
        return " ".join(words)
    return f"{words[0]} {words[-1][0].upper()}."


class ReviewSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ["id", "rating", "body", "author_name", "created_at", "updated_at"]

    def get_author_name(self, review):
        return author_name(review.user.name)


RATING_ERROR = "Choose a rating from 1 to 5 stars."
BODY_MAX_LENGTH = 2000


class MyReviewSerializer(serializers.ModelSerializer):
    """The author's own review, hidden or not; a missing ``body`` saves as blank."""

    rating = serializers.IntegerField(
        min_value=1,
        max_value=5,
        error_messages={
            key: RATING_ERROR for key in ("required", "null", "invalid", "min_value", "max_value")
        },
    )
    body = serializers.CharField(
        allow_blank=True,
        default="",
        max_length=BODY_MAX_LENGTH,
        error_messages={"max_length": "Keep your review to 2,000 characters or fewer."},
    )

    class Meta:
        model = Review
        fields = ["id", "rating", "body", "status", "created_at", "updated_at"]
        read_only_fields = ["id", "status", "created_at", "updated_at"]
