from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import Course
from .serializers import CourseListSerializer


class CourseListView(generics.ListAPIView):
    serializer_class = CourseListSerializer
    # No authentication: a suspended user's token would otherwise 401 a public page.
    authentication_classes = []
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Course.objects.published().with_ratings().order_by("-created_at")
