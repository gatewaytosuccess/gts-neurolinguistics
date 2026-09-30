from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny

from courses.models import Course

from .models import ReviewStatus
from .serializers import ReviewSerializer


class ReviewPagination(PageNumberPagination):
    page_size = 10


class CourseReviewListView(generics.ListAPIView):
    """A published course's published reviews that have a body, newest first.

    Rating-only reviews are left out here but count in the course's rating. A
    draft or unknown slug is a 404, as is a page past the last.
    """

    serializer_class = ReviewSerializer
    pagination_class = ReviewPagination
    # No authentication: a suspended user's token would otherwise 401 a public page.
    authentication_classes = []
    permission_classes = [AllowAny]

    def get_queryset(self):
        course = get_object_or_404(Course.objects.published(), slug=self.kwargs["slug"])
        return (
            course.reviews.filter(status=ReviewStatus.PUBLISHED)
            .exclude(body__regex=r"^\s*$")
            .select_related("user")
            .order_by("-created_at", "-id")
        )
