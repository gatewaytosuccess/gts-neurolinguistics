from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from courses.models import Course, CourseStatus, Lesson, Module
from enrollments.models import Enrollment, EnrollmentSource, EnrollmentStatus
from users.authentication import ClerkAuthentication
from users.models import Role, User

pytestmark = pytest.mark.django_db


def make_course(slug, status=CourseStatus.PUBLISHED, **fields):
    fields.setdefault("title", slug.replace("-", " ").title())
    fields.setdefault("price_cents", 12900)
    return Course.objects.create(slug=slug, status=status, **fields)


def add_module(course, lessons=0):
    module = Module.objects.create(course=course, title="Module", position=course.modules.count())
    for position in range(lessons):
        Lesson.objects.create(module=module, title="Lesson", position=position)
    return module


def enroll(course, status=EnrollmentStatus.ACTIVE):
    user = User.objects.create_user(email=f"learner-{Enrollment.objects.count()}@example.com")
    return Enrollment.objects.create(
        user=user, course=course, source=EnrollmentSource.MANUAL, status=status
    )


def set_timestamps(course, **days_ago):
    now = timezone.now()
    Course.objects.filter(pk=course.pk).update(
        **{field: now - timedelta(days=days) for field, days in days_ago.items()}
    )


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


def get_courses(client, params=None):
    return client.get(
        reverse("admin-course-list"), params or {}, headers={"Authorization": "Bearer stub"}
    )


def list_courses(client, params=None):
    response = get_courses(client, params)
    assert response.status_code == 200
    return response.json()


def slugs(body):
    return [item["slug"] for item in body["results"]]


def by_slug(body):
    return {item["slug"]: item for item in body["results"]}


class TestAccess:
    def test_rejects_a_request_with_no_token(self, client):
        assert client.get(reverse("admin-course-list")).status_code == 401

    def test_forbids_a_learner(self, client, signed_in):
        User.objects.create_user(email="ada@example.com", clerk_user_id="user_2abcDEF")
        assert get_courses(client).status_code == 403


class TestVisibility:
    def test_includes_drafts(self, client, admin):
        make_course("published-course")
        make_course("draft-course", status=CourseStatus.DRAFT)

        assert sorted(slugs(list_courses(client))) == ["draft-course", "published-course"]

    @pytest.mark.parametrize("status", CourseStatus.values)
    def test_status_filters(self, client, admin, status):
        make_course("published-course")
        make_course("draft-course", status=CourseStatus.DRAFT)

        (item,) = list_courses(client, {"status": status})["results"]

        assert item["status"] == status

    @pytest.mark.parametrize("status", ["", "archived", "DRAFT"])
    def test_an_unknown_status_means_all(self, client, admin, status):
        make_course("published-course")
        make_course("draft-course", status=CourseStatus.DRAFT)

        assert len(list_courses(client, {"status": status})["results"]) == 2

    def test_is_paginated_at_20(self, client, admin):
        for i in range(21):
            make_course(f"course-{i}")

        first = list_courses(client)
        second = list_courses(client, {"page": 2})

        assert first["count"] == 21
        assert len(first["results"]) == 20
        assert first["next"] is not None
        assert len(second["results"]) == 1
        assert second["previous"] is not None


class TestSearch:
    def test_matches_the_title_case_insensitively(self, client, admin):
        make_course("foundations", title="Understanding Aphasia")
        make_course("syntax", title="Syntax in the Brain")

        assert slugs(list_courses(client, {"q": "APHASIA"})) == ["foundations"]

    def test_matches_the_slug_case_insensitively(self, client, admin):
        make_course("aphasia-101", title="Foundations")
        make_course("syntax", title="Syntax in the Brain")

        assert slugs(list_courses(client, {"q": "Aphasia"})) == ["aphasia-101"]

    def test_does_not_match_the_description(self, client, admin):
        make_course("foundations", description="All about aphasia.")

        assert list_courses(client, {"q": "aphasia"})["results"] == []

    def test_blank_means_no_filter(self, client, admin):
        make_course("aphasia")
        make_course("syntax")

        assert len(list_courses(client, {"q": "  "})["results"]) == 2

    def test_combines_with_status(self, client, admin):
        make_course("aphasia-published", title="Aphasia")
        make_course("aphasia-draft", title="Aphasia", status=CourseStatus.DRAFT)
        make_course("syntax-draft", status=CourseStatus.DRAFT)

        body = list_courses(client, {"q": "aphasia", "status": CourseStatus.DRAFT})

        assert slugs(body) == ["aphasia-draft"]


class TestSort:
    @pytest.fixture
    def courses(self):
        """Created and updated orders differ, and two titles differ only by case."""
        for slug, title, created, updated in [
            ("b", "beta", 3, 0),
            ("a", "Alpha", 2, 2),
            ("c", "Gamma", 0, 3),
            ("d", "alpha", 1, 1),
        ]:
            set_timestamps(make_course(slug, title=title), created_at=created, updated_at=updated)

    def test_updated_is_most_recent_first(self, client, admin, courses):
        assert slugs(list_courses(client, {"sort": "updated"})) == ["b", "d", "a", "c"]

    def test_defaults_to_updated(self, client, admin, courses):
        assert slugs(list_courses(client)) == ["b", "d", "a", "c"]

    def test_title_ignores_case_and_breaks_ties_by_updated(self, client, admin, courses):
        assert slugs(list_courses(client, {"sort": "title"})) == ["d", "a", "b", "c"]

    def test_created_is_newest_first(self, client, admin, courses):
        assert slugs(list_courses(client, {"sort": "created"})) == ["c", "d", "a", "b"]

    def test_an_unknown_sort_behaves_like_updated(self, client, admin, courses):
        assert slugs(list_courses(client, {"sort": "price"})) == ["b", "d", "a", "c"]


class TestCounts:
    def test_counts_modules_lessons_and_active_enrollments(self, client, admin):
        course = make_course("foundations")
        add_module(course, lessons=2)
        add_module(course, lessons=3)
        add_module(course)
        enroll(course)
        enroll(course)

        item = by_slug(list_courses(client))["foundations"]

        assert item["module_count"] == 3
        assert item["lesson_count"] == 5
        assert item["active_enrollment_count"] == 2

    def test_excludes_revoked_enrollments(self, client, admin):
        course = make_course("foundations")
        enroll(course)
        enroll(course, status=EnrollmentStatus.REVOKED)

        assert by_slug(list_courses(client))["foundations"]["active_enrollment_count"] == 1

    def test_an_empty_course_counts_zero(self, client, admin):
        make_course("empty", status=CourseStatus.DRAFT)

        item = by_slug(list_courses(client))["empty"]

        assert item["module_count"] == 0
        assert item["lesson_count"] == 0
        assert item["active_enrollment_count"] == 0

    def test_counts_each_course_separately(self, client, admin):
        add_module(make_course("big"), lessons=4)
        add_module(make_course("small"), lessons=1)

        body = by_slug(list_courses(client))

        assert body["big"]["lesson_count"] == 4
        assert body["small"]["lesson_count"] == 1

    def test_does_not_query_per_course(self, client, admin, django_assert_num_queries):
        for i in range(3):
            course = make_course(f"course-{i}")
            add_module(course, lessons=2)
            enroll(course)

        # The user lookup, the paginator's count, one page of annotated courses.
        with django_assert_num_queries(3):
            list_courses(client)


class TestPayload:
    def test_returns_the_admin_fields(self, client, admin):
        make_course("foundations", title="Foundations", price_cents=14900)

        (item,) = list_courses(client)["results"]

        assert set(item) == {
            "id",
            "title",
            "slug",
            "status",
            "price_cents",
            "module_count",
            "lesson_count",
            "active_enrollment_count",
            "updated_at",
        }
        assert item["title"] == "Foundations"
        assert item["price_cents"] == 14900
        assert item["status"] == CourseStatus.PUBLISHED
