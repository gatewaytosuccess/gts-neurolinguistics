import pytest
from django.core.management import CommandError, call_command
from django.db.models import Count, Q

from courses.models import Course, CourseStatus, Lesson, Module
from enrollments.models import Enrollment
from reviews.models import Review, ReviewStatus
from users.models import User

pytestmark = pytest.mark.django_db

MODELS = [Course, Module, Lesson, User, Review, Enrollment]


def counts():
    return {model.__name__: model.objects.count() for model in MODELS}


@pytest.fixture
def debug(settings):
    # pytest-django forces DEBUG off.
    settings.DEBUG = True


def test_running_twice_creates_no_duplicates(debug):
    call_command("seed_courses")
    first = counts()
    call_command("seed_courses")
    assert counts() == first
    assert first["Course"] > 0


def test_refuses_without_debug(settings):
    settings.DEBUG = False
    with pytest.raises(CommandError):
        call_command("seed_courses")
    assert Course.objects.count() == 0


def test_seeds_the_cases_the_catalog_needs(debug):
    call_command("seed_courses")

    assert Course.objects.filter(status=CourseStatus.PUBLISHED).count() == 3
    assert Course.objects.filter(status=CourseStatus.DRAFT).count() == 1

    for course in Course.objects.all():
        lessons = Lesson.objects.filter(module__course=course)
        assert course.modules.count() == 2
        assert lessons.filter(is_preview=True).count() == 1
        assert not any(lesson.is_empty for lesson in lessons)

    published = Course.objects.filter(status=CourseStatus.PUBLISHED).annotate(
        published_reviews=Count("reviews", filter=Q(reviews__status=ReviewStatus.PUBLISHED))
    )
    assert published.filter(published_reviews=0).exists()
    assert Review.objects.filter(status=ReviewStatus.HIDDEN).exists()
    assert Enrollment.objects.count() == 0
