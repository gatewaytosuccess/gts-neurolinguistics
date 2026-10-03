"""Who may open which lessons of a course in the lesson viewer."""

from django.db import models
from django.http import Http404
from django.shortcuts import get_object_or_404

from courses.models import Course

from .models import Enrollment, EnrollmentStatus


class Access(models.TextChoices):
    ENROLLED = "enrolled", "Enrolled"
    ADMIN = "admin", "Admin"
    VISITOR = "visitor", "Visitor"


def access_to(user, course):
    """``enrolled`` wins over ``admin``: only an enrolled admin's progress is recorded.

    Signed-out users, revoked learners and instructors are all visitors.
    """
    if not user.is_authenticated:
        return Access.VISITOR
    enrolled = Enrollment.objects.filter(
        user=user, course=course, status=EnrollmentStatus.ACTIVE
    ).exists()
    if enrolled:
        return Access.ENROLLED
    if user.is_admin:
        return Access.ADMIN
    return Access.VISITOR


def viewable_course(user, slug):
    """The course and the user's access to it. Raises ``Http404`` for a visitor to a draft."""
    course = get_object_or_404(Course, slug=slug)
    access = access_to(user, course)
    if access == Access.VISITOR and not course.is_published:
        raise Http404
    return course, access


def is_locked(lesson, access):
    return access == Access.VISITOR and not lesson.is_preview
