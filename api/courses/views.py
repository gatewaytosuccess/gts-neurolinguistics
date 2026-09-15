from django.db.models import Q
from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import Course
from .serializers import CourseListSerializer

# Price sorts break ties by newest.
SORT_ORDERINGS = {
    "newest": ["-created_at"],
    "price_asc": ["price_cents", "-created_at"],
    "price_desc": ["-price_cents", "-created_at"],
}
DEFAULT_SORT = "newest"


class CourseListView(generics.ListAPIView):
    """Published courses.

    ``q`` matches title or description, case-insensitively; blank means no filter.
    ``sort`` is a ``SORT_ORDERINGS`` key; an unknown value falls back to ``newest``,
    never a 400.
    """

    serializer_class = CourseListSerializer
    # No authentication: a suspended user's token would otherwise 401 a public page.
    authentication_classes = []
    permission_classes = [AllowAny]

    def get_queryset(self):
        courses = Course.objects.published().with_ratings()

        query = self.request.query_params.get("q", "").strip()
        if query:
            courses = courses.filter(Q(title__icontains=query) | Q(description__icontains=query))

        sort = self.request.query_params.get("sort", DEFAULT_SORT)
        return courses.order_by(*SORT_ORDERINGS.get(sort, SORT_ORDERINGS[DEFAULT_SORT]))


class CourseDetailView(generics.RetrieveAPIView):
    """A published course by slug; drafts 404 like unknown slugs."""

    queryset = Course.objects.published().with_ratings()
    serializer_class = CourseListSerializer
    lookup_field = "slug"
    # No authentication: a suspended user's token would otherwise 401 a public page.
    authentication_classes = []
    permission_classes = [AllowAny]
