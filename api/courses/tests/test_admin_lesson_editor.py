import uuid

import pytest
from django.urls import reverse

from courses.models import Course, Lesson, Module
from users.authentication import ClerkAuthentication
from users.models import Role, User

pytestmark = pytest.mark.django_db

AUTH = {"Authorization": "Bearer stub"}


@pytest.fixture
def signed_in(monkeypatch):
    """Stubs only token verification; the status check runs for real."""
    monkeypatch.setattr(
        ClerkAuthentication, "decode_token", lambda self, token: {"sub": "user_2abcDEF"}
    )


@pytest.fixture
def admin(signed_in):
    return User.objects.create_user(
        email="ada@example.com", clerk_user_id="user_2abcDEF", role=Role.ADMIN
    )


@pytest.fixture
def learner(signed_in):
    return User.objects.create_user(email="ada@example.com", clerk_user_id="user_2abcDEF")


@pytest.fixture
def lesson():
    course = Course.objects.create(slug="foundations", title="Foundations", price_cents=12900)
    Module.objects.create(course=course, title="Welcome", position=1)
    module = Module.objects.create(course=course, title="Anatomy", position=2)
    Lesson.objects.create(module=module, title="Broca", position=1)
    return Lesson.objects.create(module=module, title="Wernicke", position=2)


def lesson_url(lesson_or_id):
    pk = getattr(lesson_or_id, "pk", lesson_or_id)
    return reverse("admin-lesson", kwargs={"pk": pk})


def get_lesson(client, lesson_or_id):
    return client.get(lesson_url(lesson_or_id), headers=AUTH)


def patch_lesson(client, lesson_or_id, **body):
    return client.patch(
        lesson_url(lesson_or_id), body, content_type="application/json", headers=AUTH
    )


def field_errors(response):
    assert response.status_code == 400
    return response.json()


class TestAccess:
    def test_rejects_requests_with_no_token(self, client, lesson):
        assert client.get(lesson_url(lesson)).status_code == 401
        assert client.patch(lesson_url(lesson), {}).status_code == 401

    def test_forbids_a_learner(self, client, learner, lesson):
        assert get_lesson(client, lesson).status_code == 403
        assert patch_lesson(client, lesson, title="Changed", body="Text").status_code == 403
        lesson.refresh_from_db()
        assert lesson.title == "Wernicke"
        assert lesson.body == ""


class TestRetrieve:
    def test_returns_the_lesson_with_its_module_and_course(self, client, admin, lesson):
        lesson.body = "# Heading"
        lesson.is_preview = True
        lesson.duration_seconds = 754
        lesson.save()

        response = get_lesson(client, lesson)

        assert response.status_code == 200
        module, course = lesson.module, lesson.module.course
        assert response.json() == {
            "id": str(lesson.pk),
            "title": "Wernicke",
            "body": "# Heading",
            "is_preview": True,
            "duration_seconds": 754,
            "video_key": "",
            "video_url": "",
            "slides_key": "",
            "slides_url": "",
            "position": 2,
            "is_empty": False,
            "module": {"id": str(module.pk), "title": "Anatomy", "position": 2},
            "course": {"id": str(course.pk), "title": "Foundations", "status": "draft"},
        }

    def test_an_unknown_lesson_is_not_found(self, client, admin):
        assert get_lesson(client, uuid.uuid4()).status_code == 404


class TestUpdate:
    def test_updates_the_fields(self, client, admin, lesson):
        response = patch_lesson(
            client,
            lesson,
            title="Wernicke's area",
            body="- one\n- two",
            is_preview=True,
            duration_seconds=90,
        )

        assert response.status_code == 200
        lesson.refresh_from_db()
        assert lesson.title == "Wernicke's area"
        assert lesson.body == "- one\n- two"
        assert lesson.is_preview is True
        assert lesson.duration_seconds == 90

    def test_returns_the_updated_lesson(self, client, admin, lesson):
        body = patch_lesson(client, lesson, body="Text").json()

        assert body["body"] == "Text"
        assert body["is_empty"] is False
        assert body["course"]["title"] == "Foundations"

    def test_only_the_fields_given_change(self, client, admin, lesson):
        lesson.body = "Text"
        lesson.duration_seconds = 60
        lesson.save()

        patch_lesson(client, lesson, is_preview=True)

        lesson.refresh_from_db()
        assert lesson.body == "Text"
        assert lesson.duration_seconds == 60

    def test_a_body_can_be_cleared(self, client, admin, lesson):
        lesson.body = "Text"
        lesson.save()

        body = patch_lesson(client, lesson, body="").json()

        assert body["is_empty"] is True

    def test_raw_html_is_stored_as_written(self, client, admin, lesson):
        patch_lesson(client, lesson, body="<script>alert(1)</script>")

        lesson.refresh_from_db()
        assert lesson.body == "<script>alert(1)</script>"

    @pytest.mark.parametrize("field", ["id", "position", "is_empty"])
    def test_ignores_read_only_fields(self, client, admin, lesson, field):
        before = get_lesson(client, lesson).json()[field]

        response = patch_lesson(client, lesson, **{field: 99})

        assert response.status_code == 200
        assert response.json()[field] == before

    def test_ignores_a_module_in_the_body(self, client, admin, lesson):
        other = Module.objects.get(title="Welcome")

        patch_lesson(client, lesson, module=str(other.pk))

        lesson.refresh_from_db()
        assert lesson.module.title == "Anatomy"

    def test_refuses_a_blank_title(self, client, admin, lesson):
        assert "title" in field_errors(patch_lesson(client, lesson, title=""))

    def test_put_is_not_allowed(self, client, admin, lesson):
        response = client.put(
            lesson_url(lesson), {"title": "New"}, content_type="application/json", headers=AUTH
        )

        assert response.status_code == 405

    def test_an_unknown_lesson_is_not_found(self, client, admin):
        assert patch_lesson(client, uuid.uuid4(), title="New").status_code == 404


class TestDuration:
    def test_can_be_cleared(self, client, admin, lesson):
        lesson.duration_seconds = 60
        lesson.save()

        assert patch_lesson(client, lesson, duration_seconds=None).status_code == 200
        lesson.refresh_from_db()
        assert lesson.duration_seconds is None

    def test_accepts_one_second(self, client, admin, lesson):
        assert patch_lesson(client, lesson, duration_seconds=1).status_code == 200

    @pytest.mark.parametrize("duration_seconds", [0, -1])
    def test_refuses_zero_or_below(self, client, admin, lesson, duration_seconds):
        errors = field_errors(patch_lesson(client, lesson, duration_seconds=duration_seconds))

        assert errors == {"duration_seconds": ["The duration must be greater than 0."]}

    def test_refuses_a_fraction(self, client, admin, lesson):
        assert "duration_seconds" in field_errors(
            patch_lesson(client, lesson, duration_seconds=1.5)
        )
