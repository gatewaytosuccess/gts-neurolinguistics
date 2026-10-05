import uuid
from urllib.parse import parse_qs, urlparse

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
BUCKET = "gts-private"


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


def lesson_url(slug, lesson_or_id):
    pk = getattr(lesson_or_id, "pk", lesson_or_id)
    return reverse("learn-lesson", kwargs={"slug": slug, "pk": pk})


def get_lesson(client, course, lesson_or_id, signed_in=True):
    headers = AUTH if signed_in else {}
    return client.get(lesson_url(course.slug, lesson_or_id), headers=headers)


def presigned_get(url):
    """The key and expiry a presigned GET URL signs for, after checking its bucket."""
    parsed = urlparse(url)
    assert parsed.netloc == f"{BUCKET}.s3.us-east-2.amazonaws.com"
    query = parse_qs(parsed.query)
    assert "X-Amz-Signature" in query
    return parsed.path.lstrip("/"), int(query["X-Amz-Expires"][0])


def access_of(response):
    assert response.status_code == 200
    return response.json()["access"]


def assert_locked(response, course):
    assert response.status_code == 403
    assert response.json() == {
        "detail": "This lesson is for enrolled learners.",
        "code": "lesson_locked",
        "course": {"id": str(course.pk), "title": course.title, "slug": course.slug},
    }


class TestSignedOutVisitor:
    def test_opens_a_preview_lesson_of_a_published_course(self, client):
        course = make_course()

        response = get_lesson(client, course, lesson_of(course, "Intro"), signed_in=False)

        assert access_of(response) == "visitor"

    def test_is_locked_out_of_any_other_lesson(self, client):
        course = make_course()

        response = get_lesson(client, course, lesson_of(course, "Broca"), signed_in=False)

        assert_locked(response, course)

    @pytest.mark.parametrize("title", ["Intro", "Broca"])
    def test_gets_404_for_any_lesson_of_a_draft(self, client, title):
        course = make_course(status=CourseStatus.DRAFT)

        response = get_lesson(client, course, lesson_of(course, title), signed_in=False)

        assert response.status_code == 404


class TestSignedInVisitor:
    def test_opens_a_preview_lesson(self, client, ada):
        course = make_course()

        assert access_of(get_lesson(client, course, lesson_of(course, "Intro"))) == "visitor"

    def test_is_locked_out_of_any_other_lesson(self, client, ada):
        course = make_course()

        assert_locked(get_lesson(client, course, lesson_of(course, "Broca")), course)

    def test_gets_404_for_a_draft(self, client, ada):
        course = make_course(status=CourseStatus.DRAFT)

        assert get_lesson(client, course, lesson_of(course, "Intro")).status_code == 404

    def test_an_enrollment_in_another_course_does_not_count(self, client, ada):
        course = make_course()
        enroll(ada, make_course("syntax"))

        assert_locked(get_lesson(client, course, lesson_of(course, "Broca")), course)

    def test_an_instructor_is_a_visitor(self, client, ada):
        User.objects.filter(pk=ada.pk).update(role=Role.INSTRUCTOR)
        course = make_course()

        assert_locked(get_lesson(client, course, lesson_of(course, "Broca")), course)


class TestEnrolledLearner:
    @pytest.mark.parametrize("title", ["Intro", "Broca", "Wernicke"])
    def test_opens_every_lesson(self, client, ada, title):
        course = make_course()
        enroll(ada, course)

        assert access_of(get_lesson(client, course, lesson_of(course, title))) == "enrolled"

    def test_opens_every_lesson_of_a_draft(self, client, ada):
        course = make_course(status=CourseStatus.DRAFT)
        enroll(ada, course)

        assert access_of(get_lesson(client, course, lesson_of(course, "Broca"))) == "enrolled"

    @pytest.mark.parametrize("source", EnrollmentSource.values)
    def test_any_source_counts(self, client, ada, source):
        course = make_course()
        enroll(ada, course, source=source)

        assert access_of(get_lesson(client, course, lesson_of(course, "Broca"))) == "enrolled"


class TestRevokedLearner:
    def test_is_locked_out_of_non_preview_lessons(self, client, ada):
        course = make_course()
        enroll(ada, course, status=EnrollmentStatus.REVOKED)

        assert_locked(get_lesson(client, course, lesson_of(course, "Broca")), course)

    def test_still_opens_a_preview_lesson(self, client, ada):
        course = make_course()
        enroll(ada, course, status=EnrollmentStatus.REVOKED)

        assert access_of(get_lesson(client, course, lesson_of(course, "Intro"))) == "visitor"

    def test_gets_404_for_a_draft(self, client, ada):
        course = make_course(status=CourseStatus.DRAFT)
        enroll(ada, course, status=EnrollmentStatus.REVOKED)

        assert get_lesson(client, course, lesson_of(course, "Broca")).status_code == 404


class TestAdmin:
    @pytest.mark.parametrize("status", CourseStatus.values)
    def test_opens_any_lesson_without_an_enrollment(self, client, admin, status):
        course = make_course(status=status)

        assert access_of(get_lesson(client, course, lesson_of(course, "Broca"))) == "admin"

    def test_an_enrolled_admin_is_enrolled(self, client, admin):
        course = make_course()
        enroll(admin, course)

        assert access_of(get_lesson(client, course, lesson_of(course, "Broca"))) == "enrolled"

    def test_a_revoked_admin_is_still_an_admin(self, client, admin):
        course = make_course()
        enroll(admin, course, status=EnrollmentStatus.REVOKED)

        assert access_of(get_lesson(client, course, lesson_of(course, "Broca"))) == "admin"


class TestSuspended:
    @pytest.mark.parametrize("enrolled", [True, False])
    def test_gets_the_suspension_refusal(self, client, ada, enrolled):
        course = make_course()
        if enrolled:
            enroll(ada, course)
        User.objects.filter(pk=ada.pk).update(status=UserStatus.SUSPENDED)

        response = get_lesson(client, course, lesson_of(course, "Intro"))

        assert response.status_code == 401
        assert response.json()["code"] == "account_suspended"


class TestUnknown:
    def test_unknown_lesson_is_404(self, client, admin):
        course = make_course()

        assert get_lesson(client, course, uuid.uuid4()).status_code == 404

    def test_malformed_lesson_id_is_404(self, client, admin):
        make_course()

        assert client.get("/api/learn/foundations/lessons/not-a-uuid/").status_code == 404

    def test_unknown_course_is_404(self, client, admin):
        course = make_course()

        response = client.get(lesson_url("unknown", lesson_of(course, "Intro")), headers=AUTH)

        assert response.status_code == 404

    def test_a_lesson_of_another_course_is_404(self, client, admin):
        course = make_course()
        other = make_course("syntax")

        assert get_lesson(client, course, lesson_of(other, "Intro")).status_code == 404


class TestPayload:
    def test_returns_the_lesson_with_its_module_and_course(self, client, ada):
        course = make_course()
        enroll(ada, course)
        broca = lesson_of(course, "Broca")

        body = get_lesson(client, course, broca).json()

        assert body == {
            "id": str(broca.pk),
            "title": "Broca",
            "module": {"title": "Anatomy", "position": 2},
            "course": {"id": str(course.pk), "title": "Foundations", "slug": "foundations"},
            "body": "B",
            "video_url": "",
            "slides_url": "",
            "previous_lesson_id": str(lesson_of(course, "Intro").pk),
            "next_lesson_id": str(lesson_of(course, "Wernicke").pk),
            "access": "enrolled",
            "progress": {"status": "not_started", "last_position_seconds": 0},
        }

    def test_signs_urls_that_expire_after_four_hours(self, client, ada, s3):
        course = make_course()
        enroll(ada, course)
        broca = lesson_of(course, "Broca")
        video_key = f"lessons/{broca.pk}/talk.mp4"
        slides_key = f"lessons/{broca.pk}/deck.pdf"
        Lesson.objects.filter(pk=broca.pk).update(video_key=video_key, slides_key=slides_key)

        body = get_lesson(client, course, broca).json()

        assert presigned_get(body["video_url"]) == (video_key, 4 * 60 * 60)
        assert presigned_get(body["slides_url"]) == (slides_key, 4 * 60 * 60)


class TestProgress:
    def test_returns_the_enrolled_learners_own_progress(self, client, ada, grace):
        course = make_course()
        enroll(ada, course)
        broca = lesson_of(course, "Broca")
        LessonProgress.objects.create(
            user=ada, lesson=broca, status=ProgressStatus.IN_PROGRESS, last_position_seconds=95
        )
        LessonProgress.objects.create(
            user=grace,
            lesson=broca,
            status=ProgressStatus.COMPLETED,
            last_position_seconds=600,
            completed_at=timezone.now(),
        )

        body = get_lesson(client, course, broca).json()

        assert body["progress"] == {"status": "in_progress", "last_position_seconds": 95}

    def test_is_null_for_a_visitor(self, client):
        course = make_course()

        body = get_lesson(client, course, lesson_of(course, "Intro"), signed_in=False).json()

        assert body["progress"] is None

    def test_is_null_for_an_admin_who_is_not_enrolled(self, client, admin):
        course = make_course()
        broca = lesson_of(course, "Broca")
        LessonProgress.objects.create(user=admin, lesson=broca, last_position_seconds=95)

        assert get_lesson(client, course, broca).json()["progress"] is None

    def test_is_null_for_a_revoked_learner_whose_rows_remain(self, client, ada):
        course = make_course()
        enroll(ada, course, status=EnrollmentStatus.REVOKED)
        intro = lesson_of(course, "Intro")
        LessonProgress.objects.create(user=ada, lesson=intro, last_position_seconds=95)

        assert get_lesson(client, course, intro).json()["progress"] is None


class TestNeighbours:
    def test_previous_and_next_cross_module_boundaries(self, client, ada):
        course = make_course()
        enroll(ada, course)
        intro, broca, wernicke = (lesson_of(course, t) for t in ("Intro", "Broca", "Wernicke"))

        first = get_lesson(client, course, intro).json()
        last = get_lesson(client, course, wernicke).json()

        assert first["previous_lesson_id"] is None
        assert first["next_lesson_id"] == str(broca.pk)
        assert last["previous_lesson_id"] == str(broca.pk)
        assert last["next_lesson_id"] is None

    def test_a_lone_lesson_has_no_neighbours(self, client, admin):
        course = Course.objects.create(slug="solo", title="Solo", price_cents=100)
        module = Module.objects.create(course=course, title="Only", position=1)
        lesson = Lesson.objects.create(module=module, title="Only", position=1)

        body = get_lesson(client, course, lesson).json()

        assert body["previous_lesson_id"] is None
        assert body["next_lesson_id"] is None

    def test_follows_module_order_not_creation_order(self, client, admin):
        course = make_course()
        Module.objects.filter(course=course, title="Welcome").update(position=3)
        intro, wernicke = lesson_of(course, "Intro"), lesson_of(course, "Wernicke")

        body = get_lesson(client, course, intro).json()

        assert body["previous_lesson_id"] == str(wernicke.pk)
        assert body["next_lesson_id"] is None
