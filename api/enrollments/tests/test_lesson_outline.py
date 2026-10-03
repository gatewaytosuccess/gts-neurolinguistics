import pytest
from django.urls import reverse

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


def complete(user, course, *titles):
    for title in titles:
        LessonProgress.objects.create(
            user=user, lesson=lesson_of(course, title), status=ProgressStatus.COMPLETED
        )


def get_outline(client, slug="foundations", signed_in=True):
    headers = AUTH if signed_in else {}
    return client.get(reverse("learn-outline", kwargs={"slug": slug}), headers=headers)


def outline_of(response):
    assert response.status_code == 200
    return response.json()


def lessons_by_title(body):
    return {lesson["title"]: lesson for module in body["modules"] for lesson in module["lessons"]}


def locked_titles(body):
    return {title for title, lesson in lessons_by_title(body).items() if lesson["locked"]}


def completed_titles(body):
    return {title for title, lesson in lessons_by_title(body).items() if lesson["completed"]}


class TestSignedOutVisitor:
    def test_sees_the_whole_curriculum_with_non_preview_lessons_locked(self, client):
        make_course()

        body = outline_of(get_outline(client, signed_in=False))

        assert body["access"] == "visitor"
        assert set(lessons_by_title(body)) == {"Intro", "Broca", "Wernicke"}
        assert locked_titles(body) == {"Broca", "Wernicke"}

    def test_gets_404_for_a_draft(self, client):
        make_course(status=CourseStatus.DRAFT)

        assert get_outline(client, signed_in=False).status_code == 404


class TestSignedInVisitor:
    def test_sees_non_preview_lessons_locked(self, client, ada):
        make_course()

        body = outline_of(get_outline(client))

        assert body["access"] == "visitor"
        assert locked_titles(body) == {"Broca", "Wernicke"}

    def test_gets_404_for_a_draft(self, client, ada):
        make_course(status=CourseStatus.DRAFT)

        assert get_outline(client).status_code == 404

    def test_an_enrollment_in_another_course_does_not_count(self, client, ada):
        make_course()
        enroll(ada, make_course("syntax"))

        assert outline_of(get_outline(client))["access"] == "visitor"


class TestEnrolledLearner:
    @pytest.mark.parametrize("status", CourseStatus.values)
    def test_sees_nothing_locked(self, client, ada, status):
        course = make_course(status=status)
        enroll(ada, course)

        body = outline_of(get_outline(client))

        assert body["access"] == "enrolled"
        assert locked_titles(body) == set()


class TestRevokedLearner:
    def test_is_a_visitor(self, client, ada):
        course = make_course()
        enroll(ada, course, status=EnrollmentStatus.REVOKED)

        body = outline_of(get_outline(client))

        assert body["access"] == "visitor"
        assert locked_titles(body) == {"Broca", "Wernicke"}

    def test_gets_404_for_a_draft(self, client, ada):
        course = make_course(status=CourseStatus.DRAFT)
        enroll(ada, course, status=EnrollmentStatus.REVOKED)

        assert get_outline(client).status_code == 404


class TestAdmin:
    @pytest.mark.parametrize("status", CourseStatus.values)
    def test_sees_nothing_locked_without_an_enrollment(self, client, admin, status):
        make_course(status=status)

        body = outline_of(get_outline(client))

        assert body["access"] == "admin"
        assert locked_titles(body) == set()

    def test_an_enrolled_admin_is_enrolled(self, client, admin):
        enroll(admin, make_course())

        assert outline_of(get_outline(client))["access"] == "enrolled"


class TestSuspended:
    def test_gets_the_suspension_refusal(self, client, ada):
        enroll(ada, make_course())
        User.objects.filter(pk=ada.pk).update(status=UserStatus.SUSPENDED)

        response = get_outline(client)

        assert response.status_code == 401
        assert response.json()["code"] == "account_suspended"


class TestUnknown:
    def test_unknown_course_is_404(self, client, admin):
        make_course()

        assert get_outline(client, slug="unknown").status_code == 404


class TestCompleted:
    def test_marks_the_learners_completed_lessons(self, client, ada):
        course = make_course()
        enroll(ada, course)
        complete(ada, course, "Intro", "Wernicke")
        LessonProgress.objects.create(
            user=ada, lesson=lesson_of(course, "Broca"), status=ProgressStatus.IN_PROGRESS
        )

        body = outline_of(get_outline(client))

        assert completed_titles(body) == {"Intro", "Wernicke"}
        assert (body["completed_lesson_count"], body["lesson_count"]) == (2, 3)

    def test_ignores_other_learners_progress(self, client, ada, grace):
        course = make_course()
        enroll(ada, course)
        enroll(grace, course)
        complete(grace, course, "Intro", "Broca")
        complete(ada, course, "Wernicke")

        body = outline_of(get_outline(client))

        assert completed_titles(body) == {"Wernicke"}
        assert body["completed_lesson_count"] == 1

    def test_ignores_progress_in_other_courses(self, client, ada):
        course = make_course()
        other = make_course("syntax")
        enroll(ada, course)
        enroll(ada, other)
        complete(ada, other, "Intro")

        body = outline_of(get_outline(client))

        assert completed_titles(body) == set()
        assert body["completed_lesson_count"] == 0

    def test_a_revoked_learner_sees_nothing_completed(self, client, ada):
        course = make_course()
        enroll(ada, course, status=EnrollmentStatus.REVOKED)
        complete(ada, course, "Intro", "Broca")

        body = outline_of(get_outline(client))

        assert completed_titles(body) == set()
        assert (body["completed_lesson_count"], body["lesson_count"]) == (0, 3)

    def test_an_unenrolled_admin_sees_nothing_completed(self, client, admin):
        course = make_course()
        complete(admin, course, "Intro")

        body = outline_of(get_outline(client))

        assert completed_titles(body) == set()
        assert body["completed_lesson_count"] == 0


class TestPayload:
    def test_returns_the_course_and_its_curriculum_in_order(self, client, ada):
        course = make_course()
        enroll(ada, course)
        complete(ada, course, "Intro")
        welcome = Module.objects.get(course=course, title="Welcome")
        anatomy = Module.objects.get(course=course, title="Anatomy")
        intro, broca, wernicke = (lesson_of(course, t) for t in ("Intro", "Broca", "Wernicke"))
        Lesson.objects.filter(pk=broca.pk).update(
            video_key=f"lessons/{broca.pk}/talk.mp4", duration_seconds=540
        )

        body = outline_of(get_outline(client))

        assert body == {
            "course": {"id": str(course.pk), "title": "Foundations", "slug": "foundations"},
            "access": "enrolled",
            "lesson_count": 3,
            "completed_lesson_count": 1,
            "modules": [
                {
                    "id": str(welcome.pk),
                    "title": "Welcome",
                    "position": 1,
                    "lessons": [
                        {
                            "id": str(intro.pk),
                            "title": "Intro",
                            "duration_seconds": None,
                            "is_preview": True,
                            "kinds": ["text"],
                            "locked": False,
                            "completed": True,
                        }
                    ],
                },
                {
                    "id": str(anatomy.pk),
                    "title": "Anatomy",
                    "position": 2,
                    "lessons": [
                        {
                            "id": str(broca.pk),
                            "title": "Broca",
                            "duration_seconds": 540,
                            "is_preview": False,
                            "kinds": ["video", "text"],
                            "locked": False,
                            "completed": False,
                        },
                        {
                            "id": str(wernicke.pk),
                            "title": "Wernicke",
                            "duration_seconds": None,
                            "is_preview": False,
                            "kinds": ["text"],
                            "locked": False,
                            "completed": False,
                        },
                    ],
                },
            ],
        }

    def test_follows_module_order_not_creation_order(self, client, admin):
        course = make_course()
        Module.objects.filter(course=course, title="Welcome").update(position=3)

        body = outline_of(get_outline(client))

        assert [module["title"] for module in body["modules"]] == ["Anatomy", "Welcome"]

    def test_lists_a_module_without_lessons(self, client, admin):
        course = make_course()
        Module.objects.create(course=course, title="Coming up", position=3)

        body = outline_of(get_outline(client))

        assert body["modules"][-1]["lessons"] == []
        assert body["lesson_count"] == 3
