from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from courses.models import Course
from enrollments.models import Enrollment, EnrollmentSource, EnrollmentStatus
from users.authentication import ClerkAuthentication
from users.models import Role, User, UserStatus

pytestmark = pytest.mark.django_db

ADMIN_EMAIL = "admin@example.com"


@pytest.fixture
def signed_in(monkeypatch):
    """Stubs only token verification; the status check runs for real."""
    monkeypatch.setattr(
        ClerkAuthentication, "decode_token", lambda self, token: {"sub": "user_admin"}
    )


@pytest.fixture
def admin(signed_in):
    user = User.objects.create_user(email=ADMIN_EMAIL, clerk_user_id="user_admin", role=Role.ADMIN)
    # Older than every user a test makes, so it sorts last by newest.
    set_created(user, days_ago=365)
    return user


def make_user(email, days_ago=None, **fields):
    user = User.objects.create_user(email=email, **fields)
    if days_ago is not None:
        set_created(user, days_ago)
    return user


def set_created(user, days_ago):
    User.objects.filter(pk=user.pk).update(created_at=timezone.now() - timedelta(days=days_ago))


def enroll(user, slug, status=EnrollmentStatus.ACTIVE):
    course, _ = Course.objects.get_or_create(
        slug=slug, defaults={"title": slug.title(), "price_cents": 12900}
    )
    return Enrollment.objects.create(
        user=user, course=course, source=EnrollmentSource.MANUAL, status=status
    )


def get_users(client, params=None):
    return client.get(
        reverse("admin-user-list"), params or {}, headers={"Authorization": "Bearer stub"}
    )


def list_users(client, params=None):
    response = get_users(client, params)
    assert response.status_code == 200, response.json()
    return response.json()


def emails(body):
    return [item["email"] for item in body["results"]]


def others(body):
    """The listed emails, minus the signed-in admin's."""
    return [email for email in emails(body) if email != ADMIN_EMAIL]


def by_email(body):
    return {item["email"]: item for item in body["results"]}


class TestAccess:
    def test_rejects_a_request_with_no_token(self, client):
        assert client.get(reverse("admin-user-list")).status_code == 401

    @pytest.mark.parametrize("role", [Role.LEARNER, Role.INSTRUCTOR])
    def test_forbids_every_other_role(self, client, signed_in, role):
        User.objects.create_user(email=ADMIN_EMAIL, clerk_user_id="user_admin", role=role)
        assert get_users(client).status_code == 403


class TestStatusFilter:
    @pytest.fixture
    def users(self):
        make_user("active@example.com")
        make_user("suspended@example.com", status=UserStatus.SUSPENDED)
        make_user("deleted@example.com", status=UserStatus.DELETED)

    def test_no_status_includes_deleted(self, client, admin, users):
        assert sorted(others(list_users(client))) == [
            "active@example.com",
            "deleted@example.com",
            "suspended@example.com",
        ]

    def test_blank_means_no_filter(self, client, admin, users):
        assert len(others(list_users(client, {"status": ""}))) == 3

    @pytest.mark.parametrize(
        "status", [UserStatus.ACTIVE, UserStatus.SUSPENDED, UserStatus.DELETED]
    )
    def test_filters_to_one_status(self, client, admin, users, status):
        (email,) = others(list_users(client, {"status": status}))

        assert email == f"{status}@example.com"

    @pytest.mark.parametrize("status", ["archived", "ACTIVE"])
    def test_an_unknown_status_is_a_400(self, client, admin, status):
        response = get_users(client, {"status": status})

        assert response.status_code == 400
        assert "status" in response.json()


class TestRoleFilter:
    @pytest.fixture
    def users(self):
        make_user("learner@example.com")
        make_user("instructor@example.com", role=Role.INSTRUCTOR)

    def test_filters_to_learners(self, client, admin, users):
        assert emails(list_users(client, {"role": Role.LEARNER})) == ["learner@example.com"]

    def test_filters_to_instructors(self, client, admin, users):
        assert emails(list_users(client, {"role": Role.INSTRUCTOR})) == ["instructor@example.com"]

    def test_filters_to_admins(self, client, admin, users):
        assert emails(list_users(client, {"role": Role.ADMIN})) == [ADMIN_EMAIL]

    def test_blank_means_no_filter(self, client, admin, users):
        assert len(list_users(client, {"role": ""})["results"]) == 3

    def test_an_unknown_role_is_a_400(self, client, admin):
        response = get_users(client, {"role": "staff"})

        assert response.status_code == 400
        assert "role" in response.json()


class TestSearch:
    def test_matches_part_of_the_name_case_insensitively(self, client, admin):
        make_user("ada@example.com", name="Ada Lovelace")
        make_user("grace@example.com", name="Grace Hopper")

        assert emails(list_users(client, {"q": "LOVE"})) == ["ada@example.com"]

    def test_matches_part_of_the_email_case_insensitively(self, client, admin):
        make_user("ada.lovelace@example.com", name="Ada")
        make_user("grace@example.com", name="Grace")

        assert emails(list_users(client, {"q": "Lovelace@"})) == ["ada.lovelace@example.com"]

    def test_blank_means_no_filter(self, client, admin):
        make_user("ada@example.com")
        make_user("grace@example.com")

        assert len(others(list_users(client, {"q": "  "}))) == 2


class TestCombinedFilters:
    @pytest.fixture
    def users(self):
        make_user("ada.learner@example.com")
        make_user("ada.suspended@example.com", status=UserStatus.SUSPENDED)
        make_user("ada.instructor@example.com", role=Role.INSTRUCTOR, status=UserStatus.SUSPENDED)
        make_user("grace.suspended@example.com", status=UserStatus.SUSPENDED)

    def test_search_role_and_status_all_apply(self, client, admin, users):
        body = list_users(
            client, {"q": "ada", "role": Role.LEARNER, "status": UserStatus.SUSPENDED}
        )

        assert emails(body) == ["ada.suspended@example.com"]

    def test_filters_survive_pagination(self, client, admin):
        for i in range(21):
            make_user(f"ada-{i}@example.com", status=UserStatus.SUSPENDED)
            make_user(f"ada-active-{i}@example.com")

        params = {"q": "ada", "status": UserStatus.SUSPENDED}
        first = list_users(client, params)
        second = list_users(client, {**params, "page": 2})

        assert first["count"] == 21
        assert len(first["results"]) == 20
        assert "status=suspended" in first["next"]
        assert "q=ada" in first["next"]
        assert len(second["results"]) == 1
        assert {item["status"] for item in first["results"] + second["results"]} == {"suspended"}


class TestPagination:
    def test_is_paginated_at_20(self, client, admin):
        for i in range(20):
            make_user(f"learner-{i}@example.com")

        first = list_users(client)
        second = list_users(client, {"page": 2})

        assert first["count"] == 21
        assert len(first["results"]) == 20
        assert len(second["results"]) == 1

    def test_a_page_past_the_last_is_a_404(self, client, admin):
        assert get_users(client, {"page": 2}).status_code == 404


class TestSort:
    @pytest.fixture
    def users(self):
        """Created, name and email orders all differ; two names differ only by case."""
        make_user("delta@example.com", name="beta", days_ago=3)
        make_user("Charlie@example.com", name="Alpha", days_ago=2)
        make_user("bravo@example.com", name="Gamma", days_ago=0)
        make_user("alpha@example.com", name="alpha", days_ago=1)

    def test_newest_is_most_recent_first(self, client, admin, users):
        assert others(list_users(client, {"sort": "newest"})) == [
            "bravo@example.com",
            "alpha@example.com",
            "Charlie@example.com",
            "delta@example.com",
        ]

    def test_defaults_to_newest(self, client, admin, users):
        assert others(list_users(client)) == others(list_users(client, {"sort": "newest"}))

    def test_name_ignores_case_and_breaks_ties_by_newest(self, client, admin, users):
        assert emails(list_users(client, {"sort": "name", "role": Role.LEARNER})) == [
            "alpha@example.com",
            "Charlie@example.com",
            "delta@example.com",
            "bravo@example.com",
        ]

    def test_email_ignores_case(self, client, admin, users):
        assert emails(list_users(client, {"sort": "email"})) == [
            ADMIN_EMAIL,
            "alpha@example.com",
            "bravo@example.com",
            "Charlie@example.com",
            "delta@example.com",
        ]

    def test_email_breaks_ties_by_newest(self, client, admin):
        # Emails are unique, so only a case difference can tie them.
        make_user("ada@example.com", days_ago=2)
        make_user("ADA@example.com", days_ago=1)

        assert others(list_users(client, {"sort": "email"})) == [
            "ADA@example.com",
            "ada@example.com",
        ]

    def test_an_unknown_sort_behaves_like_newest(self, client, admin, users):
        assert others(list_users(client, {"sort": "role"})) == others(list_users(client))


class TestEnrollmentCount:
    def test_counts_active_enrollments(self, client, admin):
        ada = make_user("ada@example.com")
        enroll(ada, "foundations")
        enroll(ada, "syntax")

        assert by_email(list_users(client))["ada@example.com"]["active_enrollment_count"] == 2

    def test_ignores_revoked_enrollments(self, client, admin):
        ada = make_user("ada@example.com")
        enroll(ada, "foundations")
        enroll(ada, "syntax", status=EnrollmentStatus.REVOKED)

        assert by_email(list_users(client))["ada@example.com"]["active_enrollment_count"] == 1

    def test_counts_each_user_separately(self, client, admin):
        ada = make_user("ada@example.com")
        grace = make_user("grace@example.com")
        enroll(ada, "foundations")
        enroll(grace, "foundations")
        enroll(grace, "syntax")

        body = by_email(list_users(client))

        assert body["ada@example.com"]["active_enrollment_count"] == 1
        assert body["grace@example.com"]["active_enrollment_count"] == 2
        assert body[ADMIN_EMAIL]["active_enrollment_count"] == 0

    def test_does_not_query_per_user(self, client, admin, django_assert_num_queries):
        for i in range(3):
            enroll(make_user(f"learner-{i}@example.com"), "foundations")

        # The admin lookup, the paginator's count, one page of annotated users.
        with django_assert_num_queries(3):
            list_users(client)


class TestPayload:
    def test_returns_the_admin_fields(self, client, admin):
        make_user(
            "ada@example.com",
            name="Ada Lovelace",
            avatar_url="https://img.clerk.com/ada.png",
            status=UserStatus.SUSPENDED,
            suspension_reason="Chargeback",
        )

        item = by_email(list_users(client))["ada@example.com"]

        assert set(item) == {
            "id",
            "email",
            "name",
            "avatar_url",
            "role",
            "status",
            "active_enrollment_count",
            "created_at",
        }
        assert item["name"] == "Ada Lovelace"
        assert item["avatar_url"] == "https://img.clerk.com/ada.png"
        assert item["role"] == Role.LEARNER
        assert item["status"] == UserStatus.SUSPENDED
