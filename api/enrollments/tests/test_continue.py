from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from courses.models import Course, CourseStatus, Lesson, Module
from enrollments.models import (
    Enrollment,
    EnrollmentSource,
    EnrollmentStatus,
    LessonProgress,
    ProgressStatus,
)
from users.authentication import ClerkAuthentication
from users.models import Role, User, UserStatus

pytestmark = pytest.mark.django_db

AUTH = {"Authorization": "Bearer stub"}


@pytest.fixture
def signed_in(monkeypatch):
    """Stubs only token verification; the status check runs for real."""
    monkeypatch.setattr(
        ClerkAuthentication, "decode_token", lambda self, token: {"sub": "user_2abcDEF"}
    )


@pytest.fixture
def ada(signed_in):
    return User.objects.create_user(email="ada@example.com", clerk_user_id="user_2abcDEF")


@pytest.fixture
def admin(signed_in):
    return User.objects.create_user(
        email="ada@example.com", clerk_user_id="user_2abcDEF", role=Role.ADMIN
    )


@pytest.fixture
def grace():
    return User.objects.create_user(email="grace@example.com", clerk_user_id="user_2ghiJKL")


def make_course(slug="foundations", status=CourseStatus.PUBLISHED):
    """Two modules: Welcome (Intro, a preview) and Anatomy (Broca, Wernicke)."""
    course = Course.objects.create(slug=slug, title=slug.title(), price_cents=12900, status=status)
    welcome = Module.objects.create(course=course, title="Welcome", position=1)
    anatomy = Module.objects.create(course=course, title="Anatomy", position=2)
    Lesson.objects.create(module=welcome, title="Intro", position=1, is_preview=True, body="Hi")
    # Created out of order, so curriculum order can't come from creation order.
    Lesson.objects.create(module=anatomy, title="Wernicke", position=2, body="W")
    Lesson.objects.create(module=anatomy, title="Broca", position=1, body="B")
    return course


def lesson_of(course, title):
    return Lesson.objects.get(module__course=course, title=title)


def enroll(user, course, **fields):
    fields.setdefault("source", EnrollmentSource.MANUAL)
    return Enrollment.objects.create(user=user, course=course, **fields)


def progress(user, course, title, status, minutes_ago):
    """``minutes_ago`` sets ``updated_at``, which ``auto_now`` would otherwise make now."""
    row = LessonProgress.objects.create(user=user, lesson=lesson_of(course, title), status=status)
    LessonProgress.objects.filter(pk=row.pk).update(
        updated_at=timezone.now() - timedelta(minutes=minutes_ago)
    )


def get_continue(client, slug="foundations", signed_in=True):
    headers = AUTH if signed_in else {}
    return client.get(reverse("learn-continue", kwargs={"slug": slug}), headers=headers)


def continue_of(client, slug="foundations", signed_in=True):
    response = get_continue(client, slug, signed_in)
    assert response.status_code == 200
    return response.json()


def continue_title(client, course, signed_in=True):
    lesson_id = continue_of(client, course.slug, signed_in)["lesson_id"]
    return Lesson.objects.get(pk=lesson_id).title


class TestEnrolledLearner:
    def test_with_no_progress_goes_to_the_first_lesson(self, client, ada):
        course = make_course()
        enroll(ada, course)

        assert continue_of(client)["access"] == "enrolled"
        assert continue_title(client, course) == "Intro"

    def test_goes_to_the_latest_lesson_when_it_is_in_progress(self, client, ada):
        course = make_course()
        enroll(ada, course)
        progress(ada, course, "Intro", ProgressStatus.COMPLETED, minutes_ago=30)
        progress(ada, course, "Wernicke", ProgressStatus.IN_PROGRESS, minutes_ago=5)
        progress(ada, course, "Broca", ProgressStatus.IN_PROGRESS, minutes_ago=10)

        assert continue_title(client, course) == "Wernicke"

    def test_goes_past_the_latest_lesson_when_it_is_complete(self, client, ada):
        course = make_course()
        enroll(ada, course)
        progress(ada, course, "Broca", ProgressStatus.IN_PROGRESS, minutes_ago=30)
        progress(ada, course, "Intro", ProgressStatus.COMPLETED, minutes_ago=5)

        assert continue_title(client, course) == "Broca"

    def test_stays_on_the_latest_lesson_when_it_is_complete_and_last(self, client, ada):
        course = make_course()
        enroll(ada, course)
        progress(ada, course, "Wernicke", ProgressStatus.COMPLETED, minutes_ago=5)

        assert continue_title(client, course) == "Wernicke"

    def test_goes_to_the_latest_lesson_when_every_lesson_is_complete(self, client, ada):
        course = make_course()
        enroll(ada, course)
        progress(ada, course, "Wernicke", ProgressStatus.COMPLETED, minutes_ago=30)
        progress(ada, course, "Intro", ProgressStatus.COMPLETED, minutes_ago=5)
        progress(ada, course, "Broca", ProgressStatus.COMPLETED, minutes_ago=10)

        assert continue_title(client, course) == "Intro"

    def test_ignores_other_learners_progress(self, client, ada, grace):
        course = make_course()
        enroll(ada, course)
        enroll(grace, course)
        progress(grace, course, "Broca", ProgressStatus.IN_PROGRESS, minutes_ago=5)

        assert continue_title(client, course) == "Intro"

    def test_ignores_progress_in_other_courses(self, client, ada):
        course = make_course()
        other = make_course("syntax")
        enroll(ada, course)
        enroll(ada, other)
        progress(ada, course, "Broca", ProgressStatus.IN_PROGRESS, minutes_ago=30)
        progress(ada, other, "Wernicke", ProgressStatus.IN_PROGRESS, minutes_ago=5)

        assert continue_title(client, course) == "Broca"

    def test_a_course_with_no_lessons_has_nowhere_to_go(self, client, ada):
        course = Course.objects.create(
            slug="empty", title="Empty", price_cents=0, status=CourseStatus.DRAFT
        )
        Module.objects.create(course=course, title="Welcome", position=1)
        enroll(ada, course)

        assert continue_of(client, "empty") == {"lesson_id": None, "access": "enrolled"}


class TestAdmin:
    @pytest.mark.parametrize("status", CourseStatus.values)
    def test_goes_to_the_first_lesson_ignoring_progress(self, client, admin, status):
        course = make_course(status=status)
        progress(admin, course, "Broca", ProgressStatus.IN_PROGRESS, minutes_ago=5)

        assert continue_of(client)["access"] == "admin"
        assert continue_title(client, course) == "Intro"

    def test_an_enrolled_admin_continues(self, client, admin):
        course = make_course()
        enroll(admin, course)
        progress(admin, course, "Broca", ProgressStatus.IN_PROGRESS, minutes_ago=5)

        assert continue_title(client, course) == "Broca"


class TestVisitor:
    def test_signed_out_goes_to_the_first_preview_lesson(self, client):
        course = make_course()
        Lesson.objects.filter(module__course=course).exclude(title="Wernicke").update(
            is_preview=False
        )
        Lesson.objects.filter(module__course=course, title="Wernicke").update(is_preview=True)

        assert continue_of(client, signed_in=False)["access"] == "visitor"
        assert continue_title(client, course, signed_in=False) == "Wernicke"

    def test_without_a_preview_lesson_has_nowhere_to_go(self, client, ada):
        course = make_course()
        Lesson.objects.filter(module__course=course).update(is_preview=False)

        assert continue_of(client) == {"lesson_id": None, "access": "visitor"}

    def test_a_revoked_learner_ignores_their_progress(self, client, ada):
        course = make_course()
        Lesson.objects.filter(module__course=course).update(is_preview=True)
        enroll(ada, course, status=EnrollmentStatus.REVOKED)
        progress(ada, course, "Broca", ProgressStatus.IN_PROGRESS, minutes_ago=5)

        assert continue_of(client)["access"] == "visitor"
        assert continue_title(client, course) == "Intro"

    def test_gets_404_for_a_draft(self, client, ada):
        make_course(status=CourseStatus.DRAFT)

        assert get_continue(client).status_code == 404
        assert get_continue(client, signed_in=False).status_code == 404


class TestRefusals:
    def test_suspended_gets_the_suspension_refusal(self, client, ada):
        enroll(ada, make_course())
        User.objects.filter(pk=ada.pk).update(status=UserStatus.SUSPENDED)

        response = get_continue(client)

        assert response.status_code == 401
        assert response.json()["code"] == "account_suspended"

    def test_unknown_course_is_404(self, client, admin):
        make_course()

        assert get_continue(client, slug="unknown").status_code == 404
