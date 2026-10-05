import uuid
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
    Lesson.objects.create(module=anatomy, title="Broca", position=1, body="B")
    Lesson.objects.create(module=anatomy, title="Wernicke", position=2, body="W")
    return course


def lesson_of(course, title):
    return Lesson.objects.get(module__course=course, title=title)


def enroll(user, course, **fields):
    fields.setdefault("source", EnrollmentSource.MANUAL)
    return Enrollment.objects.create(user=user, course=course, **fields)


def put_progress(client, lesson_or_id, data, signed_in=True):
    pk = getattr(lesson_or_id, "pk", lesson_or_id)
    headers = AUTH if signed_in else {}
    return client.put(
        reverse("lesson-progress", kwargs={"pk": pk}),
        data,
        content_type="application/json",
        headers=headers,
    )


def progress_of(user, lesson):
    return LessonProgress.objects.get(user=user, lesson=lesson)


def seed(user, lesson, status, **fields):
    if status == ProgressStatus.COMPLETED:
        fields.setdefault("completed_at", timezone.now() - timedelta(days=1))
    return LessonProgress.objects.create(user=user, lesson=lesson, status=status, **fields)


def backdate(progress):
    """Moves ``updated_at`` a day back, past what ``auto_now`` would set."""
    earlier = timezone.now() - timedelta(days=1)
    LessonProgress.objects.filter(pk=progress.pk).update(updated_at=earlier)
    return earlier


class TestAccess:
    def test_signed_out_is_refused(self, client):
        course = make_course()

        response = put_progress(client, lesson_of(course, "Intro"), {"opened": True}, False)

        assert response.status_code == 401
        assert not LessonProgress.objects.exists()

    def test_a_visitor_is_refused_even_on_a_preview_lesson(self, client, ada):
        course = make_course()

        response = put_progress(client, lesson_of(course, "Intro"), {"opened": True})

        assert response.status_code == 403
        assert not LessonProgress.objects.exists()

    def test_an_enrollment_in_another_course_does_not_count(self, client, ada):
        course = make_course()
        enroll(ada, make_course("syntax"))

        response = put_progress(client, lesson_of(course, "Broca"), {"completed": True})

        assert response.status_code == 403

    def test_a_revoked_learner_is_refused(self, client, ada):
        course = make_course()
        enroll(ada, course, status=EnrollmentStatus.REVOKED)

        response = put_progress(client, lesson_of(course, "Broca"), {"completed": True})

        assert response.status_code == 403
        assert not LessonProgress.objects.exists()

    def test_an_admin_who_is_not_enrolled_is_refused(self, client, admin):
        course = make_course()

        response = put_progress(client, lesson_of(course, "Broca"), {"opened": True})

        assert response.status_code == 403
        assert not LessonProgress.objects.exists()

    def test_an_enrolled_admin_is_recorded(self, client, admin):
        course = make_course()
        enroll(admin, course)

        response = put_progress(client, lesson_of(course, "Broca"), {"opened": True})

        assert response.status_code == 200
        assert progress_of(admin, lesson_of(course, "Broca")).status == ProgressStatus.IN_PROGRESS

    def test_an_enrolled_learner_records_progress_in_a_draft(self, client, ada):
        course = make_course(status=CourseStatus.DRAFT)
        enroll(ada, course)

        assert put_progress(client, lesson_of(course, "Broca"), {"opened": True}).status_code == 200

    def test_a_suspended_learner_gets_the_suspension_refusal(self, client, ada):
        course = make_course()
        enroll(ada, course)
        User.objects.filter(pk=ada.pk).update(status=UserStatus.SUSPENDED)

        response = put_progress(client, lesson_of(course, "Broca"), {"opened": True})

        assert response.status_code == 401
        assert response.json()["code"] == "account_suspended"

    def test_unknown_lesson_is_404(self, client, ada):
        assert put_progress(client, uuid.uuid4(), {"opened": True}).status_code == 404


class TestValidation:
    @pytest.mark.parametrize(
        "data",
        [
            {},
            {"opened": False},
            {"completed": "maybe"},
            {"position_seconds": -1},
            {"position_seconds": 12.5},
            {"position_seconds": "soon"},
            {"position_seconds": None},
            {"position_seconds": 2_147_483_648},
        ],
    )
    def test_refuses_a_body_that_changes_nothing_or_is_malformed(self, client, ada, data):
        course = make_course()
        enroll(ada, course)

        response = put_progress(client, lesson_of(course, "Broca"), data)

        assert response.status_code == 400
        assert not LessonProgress.objects.exists()


class TestOpened:
    def test_creates_the_row_in_progress(self, client, ada):
        course = make_course()
        enroll(ada, course)
        broca = lesson_of(course, "Broca")

        response = put_progress(client, broca, {"opened": True})

        assert response.status_code == 200
        progress = progress_of(ada, broca)
        assert progress.status == ProgressStatus.IN_PROGRESS
        assert progress.completed_at is None

    def test_starts_a_not_started_row(self, client, ada):
        course = make_course()
        enroll(ada, course)
        broca = lesson_of(course, "Broca")
        seed(ada, broca, ProgressStatus.NOT_STARTED)

        put_progress(client, broca, {"opened": True})

        assert progress_of(ada, broca).status == ProgressStatus.IN_PROGRESS

    def test_touches_an_in_progress_row(self, client, ada):
        course = make_course()
        enroll(ada, course)
        broca = lesson_of(course, "Broca")
        earlier = backdate(seed(ada, broca, ProgressStatus.IN_PROGRESS))

        put_progress(client, broca, {"opened": True})

        progress = progress_of(ada, broca)
        assert progress.status == ProgressStatus.IN_PROGRESS
        assert progress.updated_at > earlier

    def test_leaves_a_completed_lesson_complete_but_touches_it(self, client, ada):
        course = make_course()
        enroll(ada, course)
        broca = lesson_of(course, "Broca")
        seeded = seed(ada, broca, ProgressStatus.COMPLETED)
        earlier = backdate(seeded)

        put_progress(client, broca, {"opened": True})

        progress = progress_of(ada, broca)
        assert progress.status == ProgressStatus.COMPLETED
        assert progress.completed_at == seeded.completed_at
        assert progress.updated_at > earlier

    def test_does_not_duplicate_the_row(self, client, ada):
        course = make_course()
        enroll(ada, course)
        broca = lesson_of(course, "Broca")

        put_progress(client, broca, {"opened": True})
        put_progress(client, broca, {"opened": True})

        assert LessonProgress.objects.filter(user=ada, lesson=broca).count() == 1


class TestCompleted:
    def test_completes_a_lesson_never_opened(self, client, ada):
        course = make_course()
        enroll(ada, course)
        broca = lesson_of(course, "Broca")

        put_progress(client, broca, {"completed": True})

        progress = progress_of(ada, broca)
        assert progress.status == ProgressStatus.COMPLETED
        assert progress.completed_at is not None

    def test_completes_an_in_progress_lesson(self, client, ada):
        course = make_course()
        enroll(ada, course)
        broca = lesson_of(course, "Broca")
        seed(ada, broca, ProgressStatus.IN_PROGRESS)

        put_progress(client, broca, {"completed": True})

        assert progress_of(ada, broca).status == ProgressStatus.COMPLETED

    def test_completing_again_keeps_the_first_completion_time(self, client, ada):
        course = make_course()
        enroll(ada, course)
        broca = lesson_of(course, "Broca")
        seeded = seed(ada, broca, ProgressStatus.COMPLETED)

        put_progress(client, broca, {"completed": True})

        assert progress_of(ada, broca).completed_at == seeded.completed_at

    def test_un_marking_puts_it_back_in_progress(self, client, ada):
        course = make_course()
        enroll(ada, course)
        broca = lesson_of(course, "Broca")
        seed(ada, broca, ProgressStatus.COMPLETED)

        put_progress(client, broca, {"completed": False})

        progress = progress_of(ada, broca)
        assert progress.status == ProgressStatus.IN_PROGRESS
        assert progress.completed_at is None

    def test_un_marking_a_lesson_never_opened_leaves_it_in_progress(self, client, ada):
        course = make_course()
        enroll(ada, course)
        broca = lesson_of(course, "Broca")

        put_progress(client, broca, {"completed": False})

        assert progress_of(ada, broca).status == ProgressStatus.IN_PROGRESS

    def test_opened_and_completed_together_complete_it(self, client, ada):
        course = make_course()
        enroll(ada, course)
        broca = lesson_of(course, "Broca")

        put_progress(client, broca, {"opened": True, "completed": True})

        assert progress_of(ada, broca).status == ProgressStatus.COMPLETED

    def test_only_writes_the_requesters_row(self, client, ada, grace):
        course = make_course()
        enroll(ada, course)
        enroll(grace, course)
        broca = lesson_of(course, "Broca")
        seed(grace, broca, ProgressStatus.COMPLETED)

        put_progress(client, broca, {"completed": False})

        assert progress_of(grace, broca).status == ProgressStatus.COMPLETED


class TestPosition:
    def test_creates_the_row_in_progress_at_that_position(self, client, ada):
        course = make_course()
        enroll(ada, course)
        broca = lesson_of(course, "Broca")

        response = put_progress(client, broca, {"position_seconds": 95})

        assert response.status_code == 200
        assert response.json()["last_position_seconds"] == 95
        progress = progress_of(ada, broca)
        assert progress.status == ProgressStatus.IN_PROGRESS
        assert progress.last_position_seconds == 95

    def test_starts_a_not_started_row(self, client, ada):
        course = make_course()
        enroll(ada, course)
        broca = lesson_of(course, "Broca")
        seed(ada, broca, ProgressStatus.NOT_STARTED)

        put_progress(client, broca, {"position_seconds": 10})

        assert progress_of(ada, broca).status == ProgressStatus.IN_PROGRESS

    def test_overwrites_the_last_position_even_backwards(self, client, ada):
        course = make_course()
        enroll(ada, course)
        broca = lesson_of(course, "Broca")
        seed(ada, broca, ProgressStatus.IN_PROGRESS, last_position_seconds=300)

        put_progress(client, broca, {"position_seconds": 0})

        assert progress_of(ada, broca).last_position_seconds == 0

    def test_never_un_completes_a_lesson(self, client, ada):
        course = make_course()
        enroll(ada, course)
        broca = lesson_of(course, "Broca")
        seeded = seed(ada, broca, ProgressStatus.COMPLETED)

        body = put_progress(client, broca, {"position_seconds": 42}).json()

        progress = progress_of(ada, broca)
        assert progress.status == ProgressStatus.COMPLETED
        assert progress.completed_at == seeded.completed_at
        assert progress.last_position_seconds == 42
        assert body["status"] == "completed"

    def test_touches_the_row(self, client, ada):
        course = make_course()
        enroll(ada, course)
        broca = lesson_of(course, "Broca")
        earlier = backdate(seed(ada, broca, ProgressStatus.IN_PROGRESS))

        put_progress(client, broca, {"position_seconds": 5})

        assert progress_of(ada, broca).updated_at > earlier

    def test_completed_alongside_a_position_records_both(self, client, ada):
        course = make_course()
        enroll(ada, course)
        broca = lesson_of(course, "Broca")

        put_progress(client, broca, {"completed": True, "position_seconds": 600})

        progress = progress_of(ada, broca)
        assert progress.status == ProgressStatus.COMPLETED
        assert progress.last_position_seconds == 600

    def test_leaves_the_position_alone_when_not_sent(self, client, ada):
        course = make_course()
        enroll(ada, course)
        broca = lesson_of(course, "Broca")
        seed(ada, broca, ProgressStatus.IN_PROGRESS, last_position_seconds=120)

        put_progress(client, broca, {"completed": True})

        assert progress_of(ada, broca).last_position_seconds == 120

    def test_a_visitor_is_refused(self, client, ada):
        course = make_course()

        response = put_progress(client, lesson_of(course, "Intro"), {"position_seconds": 5})

        assert response.status_code == 403
        assert not LessonProgress.objects.exists()

    def test_an_admin_who_is_not_enrolled_is_refused(self, client, admin):
        course = make_course()

        response = put_progress(client, lesson_of(course, "Broca"), {"position_seconds": 5})

        assert response.status_code == 403
        assert not LessonProgress.objects.exists()


class TestPayload:
    def test_returns_the_progress_and_the_course_counts(self, client, ada, grace):
        course = make_course()
        enroll(ada, course)
        enroll(grace, course)
        broca = lesson_of(course, "Broca")
        seed(ada, lesson_of(course, "Intro"), ProgressStatus.COMPLETED)
        seed(grace, lesson_of(course, "Wernicke"), ProgressStatus.COMPLETED)

        body = put_progress(client, broca, {"completed": True}).json()

        progress = progress_of(ada, broca)
        assert body == {
            "lesson_id": str(broca.pk),
            "status": "completed",
            "completed_at": progress.completed_at.isoformat().replace("+00:00", "Z"),
            "last_position_seconds": 0,
            "lesson_count": 3,
            "completed_lesson_count": 2,
        }

    def test_completing_the_last_lesson_completes_the_course(self, client, ada):
        course = make_course()
        enroll(ada, course)
        seed(ada, lesson_of(course, "Intro"), ProgressStatus.COMPLETED)
        seed(ada, lesson_of(course, "Broca"), ProgressStatus.COMPLETED)

        body = put_progress(client, lesson_of(course, "Wernicke"), {"completed": True}).json()

        assert (body["completed_lesson_count"], body["lesson_count"]) == (3, 3)

    def test_un_marking_any_lesson_makes_it_incomplete_again(self, client, ada):
        course = make_course()
        enroll(ada, course)
        for title in ("Intro", "Broca", "Wernicke"):
            seed(ada, lesson_of(course, title), ProgressStatus.COMPLETED)

        body = put_progress(client, lesson_of(course, "Intro"), {"completed": False}).json()

        assert (body["completed_lesson_count"], body["lesson_count"]) == (2, 3)
        assert body["completed_at"] is None
