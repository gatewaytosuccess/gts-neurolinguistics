import logging

from django.db import transaction
from django.db.models import (
    BooleanField,
    Case,
    ExpressionWrapper,
    IntegerField,
    Prefetch,
    Q,
    Value,
    When,
)
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import APIView

from courses.models import Lesson, Module
from users.models import User
from users.permissions import IsAdmin

from .access import Access, is_locked, viewable_course
from .models import Enrollment, EnrollmentStatus, LessonProgress, ProgressStatus
from .progress import continue_lesson_id, curriculum_order
from .serializers import (
    AdminEnrollmentGrantSerializer,
    AdminEnrollmentSerializer,
    EnrollmentSerializer,
    OutlineModuleSerializer,
    ProgressInputSerializer,
    ViewerCourseSerializer,
    ViewerLessonSerializer,
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


class LessonOutlineView(APIView):
    """A course's whole curriculum in order, with ``locked`` and ``completed`` on each lesson.

    Authentication is optional, but a suspended account still gets 401. 404 for
    an unknown course, or a draft the requester can't see. ``completed`` and
    ``completed_lesson_count`` come from the requester's own progress, and only
    while enrolled: an admin or a revoked learner sees nothing completed.
    """

    permission_classes = [AllowAny]

    def get(self, request, slug):
        course, access = viewable_course(request.user, slug)
        # Bodies can be long, and only whether there is one is needed.
        lessons = (
            Lesson.objects.defer("body")
            .annotate(has_body=ExpressionWrapper(~Q(body=""), output_field=BooleanField()))
            .order_by("position")
        )
        modules = list(
            Module.objects.filter(course=course)
            .prefetch_related(Prefetch("lessons", queryset=lessons))
            .order_by("position")
        )
        completed_ids = set()
        if access == Access.ENROLLED:
            completed_ids = set(
                LessonProgress.objects.filter(
                    user=request.user,
                    lesson__module__course=course,
                    status=ProgressStatus.COMPLETED,
                ).values_list("lesson_id", flat=True)
            )
        context = {"access": access, "completed_ids": completed_ids}
        return Response(
            {
                "course": ViewerCourseSerializer(course).data,
                "access": access,
                "lesson_count": sum(len(module.lessons.all()) for module in modules),
                "completed_lesson_count": len(completed_ids),
                "modules": OutlineModuleSerializer(modules, many=True, context=context).data,
            }
        )


class LessonViewerView(APIView):
    """One lesson of a course, with the requester's ``access`` and its neighbours.

    Authentication is optional, but a suspended account still gets 401. 404 for
    an unknown lesson, one of another course, or any lesson of a draft course
    the requester can't see. A locked lesson answers 403 with
    ``code: "lesson_locked"`` and the ``course``.
    ``previous_lesson_id`` and ``next_lesson_id`` follow curriculum order across
    modules, and are ``null`` at either end. ``progress`` is ``null`` unless
    the requester is enrolled.
    """

    permission_classes = [AllowAny]

    def get(self, request, slug, pk):
        course, access = viewable_course(request.user, slug)
        lesson = get_object_or_404(
            Lesson.objects.select_related("module__course"), pk=pk, module__course=course
        )
        if is_locked(lesson, access):
            return Response(
                {
                    "detail": "This lesson is for enrolled learners.",
                    "code": "lesson_locked",
                    "course": ViewerCourseSerializer(course).data,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        order = curriculum_order(course)
        index = order.index(lesson.pk)
        return Response(
            {
                **ViewerLessonSerializer(lesson).data,
                "previous_lesson_id": order[index - 1] if index > 0 else None,
                "next_lesson_id": order[index + 1] if index + 1 < len(order) else None,
                "access": access,
                "progress": viewer_progress(request.user, lesson, access),
            }
        )


class ContinueView(APIView):
    """The lesson ``/learn/<slug>`` opens, as ``lesson_id``, with the requester's ``access``.

    Authentication is optional, but a suspended account still gets 401. 404 for
    an unknown course, or a draft the requester can't see. An enrolled learner
    gets their **Continue** lesson, an admin the first lesson, and a visitor the
    first preview lesson. ``lesson_id`` is ``null`` when there's no such lesson.
    """

    permission_classes = [AllowAny]

    def get(self, request, slug):
        course, access = viewable_course(request.user, slug)
        if access == Access.ENROLLED:
            lesson_id = continue_lesson_id(request.user, course)
        else:
            lessons = Lesson.objects.filter(module__course=course)
            if access == Access.VISITOR:
                lessons = lessons.filter(is_preview=True)
            lesson_id = (
                lessons.order_by("module__position", "position")
                .values_list("pk", flat=True)
                .first()
            )
        return Response({"lesson_id": lesson_id, "access": access})


def viewer_progress(user, lesson, access):
    if access != Access.ENROLLED:
        return None
    progress = LessonProgress.objects.filter(user=user, lesson=lesson).first()
    if progress is None:
        return {"status": ProgressStatus.NOT_STARTED, "last_position_seconds": 0}
    return {"status": progress.status, "last_position_seconds": progress.last_position_seconds}


class LessonProgressView(APIView):
    """Records the requester opening a lesson, marking it complete or not, or their video position.

    403 without an active enrollment in the lesson's course, admins included.
    ``opened`` and ``position_seconds`` create the row or move its
    ``updated_at``, and start a ``not_started`` lesson; neither undoes
    ``completed``. ``completed: false`` puts the lesson back to
    ``in_progress``. Answers with the lesson's progress and the course's
    ``lesson_count`` and ``completed_lesson_count``.
    """

    def put(self, request, pk):
        lesson = get_object_or_404(Lesson.objects.select_related("module"), pk=pk)
        enrollment = Enrollment.objects.filter(
            user=request.user, course_id=lesson.module.course_id, status=EnrollmentStatus.ACTIVE
        ).first()
        if enrollment is None:
            raise PermissionDenied("Only learners enrolled in this course record progress.")

        serializer = ProgressInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        completed = serializer.validated_data.get("completed")
        position = serializer.validated_data.get("position_seconds")

        with transaction.atomic():
            progress, _ = LessonProgress.objects.select_for_update().get_or_create(
                user=request.user, lesson=lesson
            )
            if progress.status == ProgressStatus.NOT_STARTED:
                progress.status = ProgressStatus.IN_PROGRESS
            if completed and progress.status != ProgressStatus.COMPLETED:
                progress.status = ProgressStatus.COMPLETED
                progress.completed_at = timezone.now()
            elif completed is False:
                progress.status = ProgressStatus.IN_PROGRESS
                progress.completed_at = None
            if position is not None:
                progress.last_position_seconds = position
            # Saved even when nothing changed, so updated_at records the visit.
            progress.save()

        counts = Enrollment.objects.with_progress().get(pk=enrollment.pk)
        return Response(
            {
                "lesson_id": lesson.pk,
                "status": progress.status,
                "completed_at": progress.completed_at,
                "last_position_seconds": progress.last_position_seconds,
                "lesson_count": counts.lesson_count,
                "completed_lesson_count": counts.completed_lesson_count,
            }
        )


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
