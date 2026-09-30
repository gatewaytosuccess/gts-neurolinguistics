from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from courses.models import Course
from enrollments.models import EnrollmentStatus

from .models import Review, ReviewStatus
from .serializers import MyReviewSerializer, ReviewSerializer


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


class MyCourseReviewView(APIView):
    """The requester's review of a published course; a draft or unknown slug is a 404.

    GET and DELETE are a 404 when they have none. PUT creates or replaces it and
    is a 403 without an active enrollment; replacing leaves ``status`` alone, so a
    hidden review stays hidden. DELETE needs no enrollment.
    """

    def get_course(self):
        return get_object_or_404(Course.objects.published(), slug=self.kwargs["slug"])

    def get_review(self):
        return get_object_or_404(Review, course=self.get_course(), user=self.request.user)

    def get(self, request, slug):
        return Response(MyReviewSerializer(self.get_review()).data)

    def put(self, request, slug):
        course = self.get_course()
        enrolled = course.enrollments.filter(
            user=request.user, status=EnrollmentStatus.ACTIVE
        ).exists()
        if not enrolled:
            raise PermissionDenied("Only learners enrolled in this course can review it.")

        serializer = MyReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review, created = Review.objects.update_or_create(
            course=course, user=request.user, defaults=serializer.validated_data
        )
        return Response(
            MyReviewSerializer(review).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request, slug):
        self.get_review().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
