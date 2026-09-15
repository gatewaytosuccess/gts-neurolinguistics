import pytest
from django.urls import reverse

from courses.models import Course, CourseStatus
from enrollments.models import Enrollment, EnrollmentSource, EnrollmentStatus
from users.authentication import ClerkAuthentication
from users.models import User, UserStatus

pytestmark = pytest.mark.django_db


def make_course(slug, status=CourseStatus.PUBLISHED):
    return Course.objects.create(slug=slug, title=slug.title(), price_cents=12900, status=status)


def enroll(user, course, **fields):
    fields.setdefault("source", EnrollmentSource.MANUAL)
    return Enrollment.objects.create(user=user, course=course, **fields)


@pytest.fixture
def ada():
    return User.objects.create_user(email="ada@example.com", clerk_user_id="user_2abcDEF")


@pytest.fixture
def signed_in(monkeypatch):
    """Stubs only token verification; the status check runs for real."""
    monkeypatch.setattr(
        ClerkAuthentication, "decode_token", lambda self, token: {"sub": "user_2abcDEF"}
    )


def get_enrollments(client):
    return client.get(reverse("user-me-enrollments"), headers={"Authorization": "Bearer stub"})


def course_slugs(response):
    assert response.status_code == 200
    return sorted(item["course_slug"] for item in response.json())


class TestAccess:
    def test_rejects_a_request_with_no_token(self, client):
        assert client.get(reverse("user-me-enrollments")).status_code == 401

    def test_rejects_a_suspended_account(self, client, ada, signed_in):
        User.objects.filter(pk=ada.pk).update(status=UserStatus.SUSPENDED)
        assert get_enrollments(client).status_code == 401


class TestScope:
    def test_returns_only_the_requesters_enrollments(self, client, ada, signed_in):
        grace = User.objects.create_user(email="grace@example.com")
        enroll(ada, make_course("foundations"))
        enroll(grace, make_course("syntax"))

        assert course_slugs(get_enrollments(client)) == ["foundations"]

    def test_excludes_revoked_enrollments(self, client, ada, signed_in):
        enroll(ada, make_course("foundations"))
        enroll(ada, make_course("syntax"), status=EnrollmentStatus.REVOKED)

        assert course_slugs(get_enrollments(client)) == ["foundations"]

    def test_includes_draft_courses(self, client, ada, signed_in):
        enroll(ada, make_course("unpublished", status=CourseStatus.DRAFT))

        assert course_slugs(get_enrollments(client)) == ["unpublished"]

    @pytest.mark.parametrize("source", EnrollmentSource.values)
    def test_includes_every_source(self, client, ada, signed_in, source):
        enroll(ada, make_course("foundations"), source=source)

        assert course_slugs(get_enrollments(client)) == ["foundations"]

    def test_is_empty_with_no_enrollments(self, client, ada, signed_in):
        assert get_enrollments(client).json() == []


class TestPayload:
    def test_returns_the_enrollment_fields(self, client, ada, signed_in):
        course = make_course("foundations")
        enroll(ada, course, source=EnrollmentSource.COMP)

        (item,) = get_enrollments(client).json()

        assert item["course_id"] == str(course.id)
        assert item["course_slug"] == "foundations"
        assert item["source"] == EnrollmentSource.COMP
        assert item["enrolled_at"]

    def test_is_unpaginated(self, client, ada, signed_in, settings):
        for i in range(settings.REST_FRAMEWORK["PAGE_SIZE"] + 1):
            enroll(ada, make_course(f"course-{i}"))

        body = get_enrollments(client).json()

        assert isinstance(body, list)
        assert len(body) == settings.REST_FRAMEWORK["PAGE_SIZE"] + 1

    def test_does_not_query_per_enrollment(
        self, client, ada, signed_in, django_assert_max_num_queries
    ):
        for i in range(3):
            enroll(ada, make_course(f"course-{i}"))

        # One for the user lookup, one for the enrollments.
        with django_assert_max_num_queries(2):
            get_enrollments(client)
