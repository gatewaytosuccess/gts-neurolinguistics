from django.db.models import Count, Prefetch, Q
from django.db.models.functions import Lower
from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.response import Response

from commerce.models import Order, OrderItem
from enrollments.models import EnrollmentStatus
from reviews.models import Review

from .models import User
from .permissions import IsAdmin
from .serializers import (
    AdminUserDetailSerializer,
    AdminUserFiltersSerializer,
    AdminUserListSerializer,
    UserSerializer,
)


@api_view(["GET"])
def me(request):
    """Safe to call right after sign-up: authentication provisions a missing row."""
    return Response(UserSerializer(request.user).data)


# Ties break by newest.
ADMIN_USER_SORT_ORDERINGS = {
    "newest": ["-created_at"],
    "name": [Lower("name"), "-created_at"],
    "email": [Lower("email"), "-created_at"],
}
ADMIN_USER_DEFAULT_SORT = "newest"


class AdminUserListView(generics.ListAPIView):
    """Every user, deleted ones included unless ``status`` says otherwise.

    ``q`` matches name or email, case-insensitively; blank means no filter.
    ``role`` and ``status`` take one value each; an unknown value is a 400.
    ``sort`` is an ``ADMIN_USER_SORT_ORDERINGS`` key; an unknown value falls back
    to ``newest``. A page past the last is a 404.
    """

    serializer_class = AdminUserListSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        filters = AdminUserFiltersSerializer(data=self.request.query_params)
        filters.is_valid(raise_exception=True)

        users = User.objects.annotate(
            active_enrollment_count=Count(
                "enrollments", filter=Q(enrollments__status=EnrollmentStatus.ACTIVE)
            )
        )

        query = self.request.query_params.get("q", "").strip()
        if query:
            users = users.filter(Q(name__icontains=query) | Q(email__icontains=query))

        for field in ("role", "status"):
            if value := filters.validated_data.get(field):
                users = users.filter(**{field: value})

        sort = self.request.query_params.get("sort", ADMIN_USER_DEFAULT_SORT)
        return users.order_by(
            *ADMIN_USER_SORT_ORDERINGS.get(sort, ADMIN_USER_SORT_ORDERINGS[ADMIN_USER_DEFAULT_SORT])
        )


class AdminUserDetailView(generics.RetrieveAPIView):
    """Any user, deleted ones included, with every order and review, newest first."""

    serializer_class = AdminUserDetailSerializer
    permission_classes = [IsAdmin]
    queryset = User.objects.prefetch_related(
        Prefetch(
            "orders",
            queryset=Order.objects.order_by("-created_at").prefetch_related(
                Prefetch(
                    "items",
                    queryset=OrderItem.objects.select_related("course").order_by("course__title"),
                )
            ),
        ),
        Prefetch(
            "reviews", queryset=Review.objects.select_related("course").order_by("-created_at")
        ),
    )
