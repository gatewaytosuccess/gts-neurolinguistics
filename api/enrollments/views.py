import logging

from django.db import transaction
from django.db.models import Case, IntegerField, Value, When
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.settings import api_settings

from users.models import User
from users.permissions import IsAdmin

from .models import Enrollment, EnrollmentStatus
from .serializers import (
    AdminEnrollmentGrantSerializer,
    AdminEnrollmentSerializer,
    EnrollmentSerializer,
)

logger = logging.getLogger(__name__)


class MyEnrollmentListView(generics.ListAPIView):
    """The requester's active enrollments, drafts included.

    Unpaginated: the catalog matches every card against the full list.
    """

    serializer_class = EnrollmentSerializer
    pagination_class = None

    def get_queryset(self):
        return Enrollment.objects.filter(
            user=self.request.user, status=EnrollmentStatus.ACTIVE
        ).select_related("course")


def admin_enrollments():
    return Enrollment.objects.select_related("course").with_progress()


class AdminUserEnrollmentListView(generics.ListCreateAPIView):
    """Every enrollment of any user, revoked ones and draft courses included.

    Active first, then newest. POST grants a course as ``manual`` or ``comp``
    and answers 201 with the new row; see ``AdminEnrollmentGrantSerializer``
    for what it refuses. Any account status can be granted to.
    """

    serializer_class = AdminEnrollmentSerializer
    permission_classes = [IsAdmin]
    pagination_class = None

    def get_queryset(self):
        user = get_object_or_404(User, pk=self.kwargs["pk"])
        return (
            admin_enrollments()
            .filter(user=user)
            .order_by(
                Case(
                    When(status=EnrollmentStatus.ACTIVE, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                ),
                "-enrolled_at",
            )
        )

    def create(self, request, pk):
        # Locked so two grants of the same course can't both pass the duplicate check.
        with transaction.atomic():
            user = get_object_or_404(User.objects.select_for_update(), pk=pk)
            serializer = AdminEnrollmentGrantSerializer(data=request.data, context={"user": user})
            serializer.is_valid(raise_exception=True)
            enrollment = Enrollment.objects.create(user=user, **serializer.validated_data)
        logger.info(
            "Admin %s granted user %s course %s as %s.",
            request.user.pk,
            user.pk,
            enrollment.course_id,
            enrollment.source,
        )
        return Response(
            self.get_serializer(admin_enrollments().get(pk=enrollment.pk)).data,
            status=status.HTTP_201_CREATED,
        )


class AdminEnrollmentRevokeView(generics.GenericAPIView):
    """Revoking a purchase refunds nothing. Answers 400 if already revoked."""

    serializer_class = AdminEnrollmentSerializer
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        with transaction.atomic():
            enrollment = get_object_or_404(Enrollment.objects.select_for_update(), pk=pk)
            if enrollment.status == EnrollmentStatus.REVOKED:
                refuse("This enrollment is already revoked.")
            enrollment.status = EnrollmentStatus.REVOKED
            enrollment.revoked_at = timezone.now()
            enrollment.save(update_fields=["status", "revoked_at"])
        log_write(request, enrollment, "revoked")
        return Response(self.get_serializer(admin_enrollments().get(pk=pk)).data)


class AdminEnrollmentRestoreView(generics.GenericAPIView):
    """Keeps ``source``, ``order_id`` and ``enrolled_at``. Answers 400 if already active."""

    serializer_class = AdminEnrollmentSerializer
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        with transaction.atomic():
            enrollment = get_object_or_404(Enrollment.objects.select_for_update(), pk=pk)
            if enrollment.status == EnrollmentStatus.ACTIVE:
                refuse("This enrollment is already active.")
            enrollment.status = EnrollmentStatus.ACTIVE
            enrollment.revoked_at = None
            enrollment.save(update_fields=["status", "revoked_at"])
        log_write(request, enrollment, "restored")
        return Response(self.get_serializer(admin_enrollments().get(pk=pk)).data)


def refuse(message):
    raise ValidationError({api_settings.NON_FIELD_ERRORS_KEY: [message]})


def log_write(request, enrollment, action):
    logger.info(
        "Admin %s %s the enrollment of user %s in course %s.",
        request.user.pk,
        action,
        enrollment.user_id,
        enrollment.course_id,
    )
