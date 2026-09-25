import uuid

import pytest
from django.urls import reverse

from courses.models import Course, CourseStatus, Lesson, Module
from users.authentication import ClerkAuthentication
from users.models import Role, User

pytestmark = pytest.mark.django_db

AUTH = {"Authorization": "Bearer stub"}


def make_course(slug, status=CourseStatus.DRAFT, **fields):
    fields.setdefault("title", slug.replace("-", " ").title())
    fields.setdefault("description", "About the course.")
    fields.setdefault("price_cents", 12900)
    return Course.objects.create(slug=slug, status=status, **fields)


def make_published(slug):
    """A published course that meets every publish rule."""
    course = make_course(slug, status=CourseStatus.PUBLISHED)
    course.thumbnail_key = f"thumbnails/{course.pk}/cover.png"
    course.save()
    module = Module.objects.create(course=course, title="Welcome", position=1)
    Lesson.objects.create(module=module, title="Hello", position=1, body="Hi.")
    return course


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


def detail_url(course_or_id):
    pk = getattr(course_or_id, "pk", course_or_id)
    return reverse("admin-course-detail", kwargs={"pk": pk})


def post_course(client, **body):
    body.setdefault("title", "Test Course")
    body.setdefault("price_cents", 12900)
    return client.post(
        reverse("admin-course-list"), body, content_type="application/json", headers=AUTH
    )


def create_course(client, **body):
    response = post_course(client, **body)
    assert response.status_code == 201, response.json()
    return response.json()


def get_course(client, course_or_id):
    return client.get(detail_url(course_or_id), headers=AUTH)


def patch_course(client, course, **body):
    return client.patch(detail_url(course), body, content_type="application/json", headers=AUTH)


def field_errors(response):
    assert response.status_code == 400
    return response.json()


class TestAccess:
    def test_rejects_requests_with_no_token(self, client):
        course = make_course("foundations")

        assert client.post(reverse("admin-course-list"), {}).status_code == 401
        assert client.get(detail_url(course)).status_code == 401
        assert client.patch(detail_url(course), {}).status_code == 401

    def test_forbids_a_learner(self, client, learner):
        course = make_course("foundations")

        assert post_course(client).status_code == 403
        assert get_course(client, course).status_code == 403
        assert patch_course(client, course, title="Changed").status_code == 403
        assert Course.objects.count() == 1
        course.refresh_from_db()
        assert course.title == "Foundations"


class TestCreate:
    def test_creates_a_platform_owned_draft(self, client, admin):
        body = create_course(
            client, title="Test Course", description="All about it.", price_cents=14900
        )

        course = Course.objects.get(pk=body["id"])
        assert course.status == CourseStatus.DRAFT
        assert course.instructor is None
        assert course.title == "Test Course"
        assert course.description == "All about it."
        assert course.price_cents == 14900

    def test_ignores_a_status_in_the_body(self, client, admin):
        body = create_course(client, status=CourseStatus.PUBLISHED)

        assert body["status"] == CourseStatus.DRAFT
        assert Course.objects.get(pk=body["id"]).status == CourseStatus.DRAFT

    def test_description_is_optional(self, client, admin):
        assert create_course(client)["description"] == ""

    @pytest.mark.parametrize("field", ["title", "price_cents"])
    def test_requires_title_and_price(self, client, admin, field):
        body = {"title": "Test Course", "price_cents": 12900}
        del body[field]

        response = client.post(
            reverse("admin-course-list"), body, content_type="application/json", headers=AUTH
        )

        assert field in field_errors(response)

    def test_returns_the_detail_fields(self, client, admin):
        body = create_course(client)

        assert set(body) == {
            "id",
            "title",
            "slug",
            "description",
            "price_cents",
            "thumbnail_key",
            "thumbnail_url",
            "status",
            "created_at",
            "updated_at",
        }


class TestSlugGeneration:
    def test_generates_the_slug_from_the_title(self, client, admin):
        assert create_course(client, title="Test Course")["slug"] == "test-course"

    def test_a_blank_slug_is_generated(self, client, admin):
        assert create_course(client, title="Test Course", slug="")["slug"] == "test-course"

    def test_appends_a_number_on_a_clash(self, client, admin):
        first = create_course(client, title="Test Course")
        second = create_course(client, title="Test Course")
        third = create_course(client, title="Test Course")

        assert [first["slug"], second["slug"], third["slug"]] == [
            "test-course",
            "test-course-2",
            "test-course-3",
        ]

    def test_skips_numbers_already_taken(self, client, admin):
        make_course("test-course")
        make_course("test-course-2")

        assert create_course(client, title="Test Course")["slug"] == "test-course-3"

    def test_drops_punctuation_and_accents(self, client, admin):
        assert create_course(client, title="  Afasia: ¿Qué es?  ")["slug"] == "afasia-que-es"

    def test_falls_back_when_the_title_has_no_slug_characters(self, client, admin):
        assert create_course(client, title="???")["slug"] == "course"

    def test_stays_within_the_maximum_length_on_a_clash(self, client, admin):
        title = "a" * 255
        make_course("a" * 255)

        slug = create_course(client, title=title)["slug"]

        assert slug == "a" * 253 + "-2"


class TestExplicitSlug:
    def test_keeps_an_explicit_slug(self, client, admin):
        assert create_course(client, title="Test Course", slug="intro")["slug"] == "intro"

    def test_refuses_an_explicit_slug_that_clashes(self, client, admin):
        make_course("intro")

        response = post_course(client, slug="intro")

        assert "slug" in field_errors(response)
        assert Course.objects.count() == 1

    def test_refuses_an_invalid_slug(self, client, admin):
        assert "slug" in field_errors(post_course(client, slug="Not a slug!"))


class TestRetrieve:
    def test_returns_a_draft(self, client, admin):
        course = make_course("foundations")

        response = get_course(client, course)

        assert response.status_code == 200
        assert response.json()["slug"] == "foundations"
        assert response.json()["status"] == CourseStatus.DRAFT

    def test_an_unknown_id_is_not_found(self, client, admin):
        assert get_course(client, uuid.uuid4()).status_code == 404


class TestUpdate:
    def test_updates_the_details(self, client, admin):
        course = make_course("foundations")

        response = patch_course(
            client, course, title="New Title", description="New.", price_cents=9900
        )

        assert response.status_code == 200
        course.refresh_from_db()
        assert course.title == "New Title"
        assert course.description == "New."
        assert course.price_cents == 9900

    def test_changing_the_title_keeps_the_slug(self, client, admin):
        course = make_course("foundations")

        patch_course(client, course, title="New Title")

        course.refresh_from_db()
        assert course.slug == "foundations"

    def test_ignores_a_status_in_the_body(self, client, admin):
        course = make_course("foundations")

        assert patch_course(client, course, status=CourseStatus.PUBLISHED).status_code == 200
        course.refresh_from_db()
        assert course.status == CourseStatus.DRAFT

    def test_put_is_not_allowed(self, client, admin):
        course = make_course("foundations")

        response = client.put(
            detail_url(course),
            {"title": "New", "price_cents": 100},
            content_type="application/json",
            headers=AUTH,
        )

        assert response.status_code == 405

    def test_an_unknown_id_is_not_found(self, client, admin):
        assert patch_course(client, uuid.uuid4(), title="New").status_code == 404


class TestDraftSlug:
    def test_can_change_a_drafts_slug(self, client, admin):
        course = make_course("foundations")

        assert patch_course(client, course, slug="intro").status_code == 200
        course.refresh_from_db()
        assert course.slug == "intro"

    def test_a_blank_slug_is_regenerated_from_the_title(self, client, admin):
        course = make_course("foundations")

        patch_course(client, course, title="Test Course", slug="")

        course.refresh_from_db()
        assert course.slug == "test-course"

    def test_regenerating_does_not_clash_with_itself(self, client, admin):
        course = make_course("test-course", title="Test Course")

        patch_course(client, course, slug="")

        course.refresh_from_db()
        assert course.slug == "test-course"

    def test_refuses_a_slug_another_course_uses(self, client, admin):
        make_course("intro")
        course = make_course("foundations")

        assert "slug" in field_errors(patch_course(client, course, slug="intro"))
        course.refresh_from_db()
        assert course.slug == "foundations"

    def test_resending_its_own_slug_is_not_a_clash(self, client, admin):
        course = make_course("foundations")

        assert patch_course(client, course, slug="foundations").status_code == 200


class TestPublishedSlugLock:
    def test_refuses_a_new_slug(self, client, admin):
        course = make_published("foundations")

        assert "slug" in field_errors(patch_course(client, course, slug="intro"))
        course.refresh_from_db()
        assert course.slug == "foundations"

    def test_refuses_a_blank_slug(self, client, admin):
        course = make_published("foundations")

        assert "slug" in field_errors(patch_course(client, course, slug=""))

    def test_accepts_the_same_slug(self, client, admin):
        course = make_published("foundations")

        response = patch_course(client, course, slug="foundations", title="New Title")

        assert response.status_code == 200
        course.refresh_from_db()
        assert course.title == "New Title"

    def test_other_fields_can_change(self, client, admin):
        course = make_published("foundations")

        assert patch_course(client, course, title="New", price_cents=100).status_code == 200


class TestPublishedDescription:
    def test_refuses_clearing_it(self, client, admin):
        course = make_published("foundations")

        errors = field_errors(patch_course(client, course, description="  "))

        assert errors == {"problems": ["The course has no description."]}
        course.refresh_from_db()
        assert course.description == "About the course."

    def test_a_draft_can_clear_it(self, client, admin):
        course = make_course("foundations")

        assert patch_course(client, course, description="").status_code == 200


class TestPrice:
    @pytest.mark.parametrize("price_cents", [0, -100])
    def test_create_refuses_zero_or_below(self, client, admin, price_cents):
        errors = field_errors(post_course(client, price_cents=price_cents))

        assert errors["price_cents"] == ["The price must be greater than 0."]
        assert not Course.objects.exists()

    @pytest.mark.parametrize("price_cents", [0, -100])
    def test_update_refuses_zero_or_below(self, client, admin, price_cents):
        course = make_course("foundations")

        errors = field_errors(patch_course(client, course, price_cents=price_cents))

        assert errors["price_cents"] == ["The price must be greater than 0."]
        course.refresh_from_db()
        assert course.price_cents == 12900

    def test_accepts_one_cent(self, client, admin):
        assert create_course(client, price_cents=1)["price_cents"] == 1

    def test_refuses_a_price_too_large_to_store(self, client, admin):
        assert "price_cents" in field_errors(post_course(client, price_cents=2**31))
