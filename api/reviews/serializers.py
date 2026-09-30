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
