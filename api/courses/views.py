from django.db.models import Count, Prefetch, Q
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import IsAdmin

from . import curriculum
from .models import Course, CourseStatus, Lesson, Module
from .serializers import (
    AdminCourseListSerializer,
    AdminCourseSerializer,
    AdminCurriculumModuleSerializer,
    AdminLessonSerializer,
    AdminModuleSerializer,
    CourseListSerializer,
    MoveLessonSerializer,
    MoveModuleSerializer,
)

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


# Ties break by most recently updated.
ADMIN_SORT_ORDERINGS = {
    "updated": ["-updated_at"],
    "title": [Lower("title"), "-updated_at"],
    "created": ["-created_at"],
}
ADMIN_DEFAULT_SORT = "updated"


class AdminCourseListView(generics.ListCreateAPIView):
    """Every course, drafts included; POST creates a draft.

    ``q`` matches title or slug, case-insensitively; blank means no filter.
    ``status`` is a ``CourseStatus`` value; missing or unknown means all.
    ``sort`` is an ``ADMIN_SORT_ORDERINGS`` key; an unknown value falls back to
    ``updated``, never a 400.
    """

    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AdminCourseSerializer
        return AdminCourseListSerializer

    def get_queryset(self):
        courses = Course.objects.with_counts()

        query = self.request.query_params.get("q", "").strip()
        if query:
            courses = courses.filter(Q(title__icontains=query) | Q(slug__icontains=query))

        status = self.request.query_params.get("status")
        if status in CourseStatus.values:
            courses = courses.filter(status=status)

        sort = self.request.query_params.get("sort", ADMIN_DEFAULT_SORT)
        return courses.order_by(
            *ADMIN_SORT_ORDERINGS.get(sort, ADMIN_SORT_ORDERINGS[ADMIN_DEFAULT_SORT])
        )


class AdminCourseDetailView(generics.RetrieveUpdateAPIView):
    """Any course, drafts included. Updates are PATCH only."""

    queryset = Course.objects.all()
    serializer_class = AdminCourseSerializer
    permission_classes = [IsAdmin]
    http_method_names = ["get", "patch", "head", "options"]


class AdminCurriculumView(generics.ListAPIView):
    """A course's modules in order, each with its lessons in order.

    ``learners_with_progress`` counts the learners whose progress a delete would
    remove: per lesson, and per module across its lessons.
    """

    serializer_class = AdminCurriculumModuleSerializer
    permission_classes = [IsAdmin]
    pagination_class = None

    def get_queryset(self):
        course = get_object_or_404(Course, pk=self.kwargs["pk"])
        lessons = Lesson.objects.annotate(learners_with_progress=Count("progress")).order_by(
            "position"
        )
        return (
            course.modules.annotate(
                learners_with_progress=Count("lessons__progress__user", distinct=True)
            )
            .prefetch_related(Prefetch("lessons", queryset=lessons))
            .order_by("position")
        )


class AdminModuleCreateView(APIView):
    """Appends a module to a course."""

    permission_classes = [IsAdmin]

    def post(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        serializer = AdminModuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        module = curriculum.add_module(course, serializer.validated_data["title"])
        return Response(AdminModuleSerializer(module).data, status=status.HTTP_201_CREATED)


class AdminModuleDetailView(generics.UpdateAPIView, generics.DestroyAPIView):
    """PATCH renames; DELETE also deletes its lessons and their progress."""

    queryset = Module.objects.all()
    serializer_class = AdminModuleSerializer
    permission_classes = [IsAdmin]
    http_method_names = ["patch", "delete", "options"]

    def perform_destroy(self, instance):
        curriculum.delete_module(instance)


class AdminModuleMoveView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        module = get_object_or_404(Module, pk=pk)
        serializer = MoveModuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        module = curriculum.move_module(module, serializer.validated_data["position"])
        return Response(AdminModuleSerializer(module).data)


class AdminLessonCreateView(APIView):
    """Appends an empty lesson to a module."""

    permission_classes = [IsAdmin]

    def post(self, request, pk):
        module = get_object_or_404(Module, pk=pk)
        serializer = AdminLessonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lesson = curriculum.add_lesson(module, serializer.validated_data["title"])
        return Response(AdminLessonSerializer(lesson).data, status=status.HTTP_201_CREATED)


class AdminLessonDetailView(generics.DestroyAPIView):
    """DELETE also deletes the lesson's progress."""

    queryset = Lesson.objects.select_related("module")
    permission_classes = [IsAdmin]

    def perform_destroy(self, instance):
        curriculum.delete_lesson(instance)


class AdminLessonMoveView(APIView):
    """Moves a lesson within its module, or to another module of the same course."""

    permission_classes = [IsAdmin]

    def post(self, request, pk):
        lesson = get_object_or_404(Lesson.objects.select_related("module"), pk=pk)
        serializer = MoveLessonSerializer(data=request.data, context={"lesson": lesson})
        serializer.is_valid(raise_exception=True)
        lesson = curriculum.move_lesson(
            lesson,
            position=serializer.validated_data.get("position"),
            module=serializer.validated_data.get("module_id"),
        )
        return Response(AdminLessonSerializer(lesson).data)
