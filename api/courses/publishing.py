"""What a course needs before it can be published, and keeping it that way once it is."""

from contextlib import contextmanager

from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import APIException

from .models import Course, CourseStatus


class Unpublishable(APIException):
    """A 400 whose body is ``{"problems": [...]}``."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "unpublishable"

    def __init__(self, problems):
        self.problems = problems
        super().__init__({"problems": problems})


def publish_problems(course):
    """Sentences for an admin, one per problem; empty when the course can be published."""
    problems = []
    if not course.title.strip():
        problems.append("The course has no title.")
    if course.price_cents <= 0:
        problems.append("The course's price must be above 0.")
    if not course.description.strip():
        problems.append("The course has no description.")
    if not course.thumbnail_key:
        problems.append("The course has no thumbnail.")

    modules = list(course.modules.prefetch_related("lessons").order_by("position"))
    if not modules:
        problems.append("The course has no modules.")
    for module in modules:
        lessons = module.lessons.all()
        if not lessons:
            problems.append(f'Module "{module.title}" has no lessons.')
        problems.extend(
            f'Lesson "{lesson.title}" in "{module.title}" is empty.'
            for lesson in lessons
            if lesson.is_empty
        )
    return problems


@contextmanager
def keeping_publishable(course_id):
    """A transaction holding the course's row lock, for an edit to it or its curriculum.

    If the course is published and the edit leaves it with publish problems, raises
    ``Unpublishable`` on exit and the edit rolls back. An unknown ``course_id`` is
    left for the edit itself to report.
    """
    with transaction.atomic():
        list(Course.objects.select_for_update().filter(pk=course_id).only("pk"))
        yield
        course = Course.objects.filter(pk=course_id).first()
        if course is not None and course.is_published:
            problems = publish_problems(course)
            if problems:
                raise Unpublishable(problems)


@transaction.atomic
def publish(course):
    """Returns the published course; raises ``Unpublishable`` instead if it has problems."""
    course = Course.objects.select_for_update().get(pk=course.pk)
    problems = publish_problems(course)
    if problems:
        raise Unpublishable(problems)
    course.status = CourseStatus.PUBLISHED
    course.save(update_fields=["status", "updated_at"])
    return course


def unpublish(course):
    """Always allowed. Enrollments are untouched."""
    course.status = CourseStatus.DRAFT
    course.save(update_fields=["status", "updated_at"])
    return course
