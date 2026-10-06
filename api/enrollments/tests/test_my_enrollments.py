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
from users.models import User, UserStatus

pytestmark = pytest.mark.django_db


def make_course(slug, status=CourseStatus.PUBLISHED):
    return Course.objects.create(slug=slug, title=slug.title(), price_cents=12900, status=status)


def make_course_with_lessons(slug, status=CourseStatus.PUBLISHED):
    """Two modules: Welcome (Intro) and Anatomy (Broca, Wernicke)."""
    course = make_course(slug, status)
    welcome = Module.objects.create(course=course, title="Welcome", position=1)
    anatomy = Module.objects.create(course=course, title="Anatomy", position=2)
    Lesson.objects.create(module=welcome, title="Intro", position=1)
    Lesson.objects.create(module=anatomy, title="Broca", position=1)
    Lesson.objects.create(module=anatomy, title="Wernicke", position=2)
    return course


def lesson_of(course, title):
    return Lesson.objects.get(module__course=course, title=title)


def enroll(user, course, days_ago=0, **fields):
    """``days_ago`` sets ``enrolled_at``, which ``auto_now_add`` would otherwise make now."""
    fields.setdefault("source", EnrollmentSource.MANUAL)
    enrollment = Enrollment.objects.create(user=user, course=course, **fields)
    Enrollment.objects.filter(pk=enrollment.pk).update(
        enrolled_at=timezone.now() - timedelta(days=days_ago)
    )
    return enrollment


def progress(user, course, title, status, minutes_ago):
    """``minutes_ago`` sets ``updated_at``, which ``auto_now`` would otherwise make now."""
    row = LessonProgress.objects.create(user=user, lesson=lesson_of(course, title), status=status)
    updated_at = timezone.now() - timedelta(minutes=minutes_ago)
    LessonProgress.objects.filter(pk=row.pk).update(updated_at=updated_at)
    return updated_at


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


def ordered_slugs(response):
    assert response.status_code == 200
    return [item["course_slug"] for item in response.json()]


def item_for(client, slug):
    return next(item for item in get_enrollments(client).json() if item["course_slug"] == slug)


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
        assert item["course_title"] == "Foundations"
        assert item["course_thumbnail_url"] == ""
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

        # The user, the enrollments, their lessons, the user's progress, the Continue titles.
        with django_assert_max_num_queries(5):
            get_enrollments(client)


class TestOrdering:
    def test_orders_by_most_recent_activity(self, client, ada, signed_in):
        for slug, minutes_ago in [("foundations", 30), ("syntax", 5), ("phonology", 60)]:
            course = make_course_with_lessons(slug)
            enroll(ada, course)
            progress(ada, course, "Intro", ProgressStatus.IN_PROGRESS, minutes_ago)

        assert ordered_slugs(get_enrollments(client)) == ["syntax", "foundations", "phonology"]

    def test_puts_courses_not_started_after_by_newest_enrollment(self, client, ada, signed_in):
        enroll(ada, make_course_with_lessons("old"), days_ago=10)
        enroll(ada, make_course_with_lessons("new"), days_ago=1)
        started = make_course_with_lessons("started")
        enroll(ada, started, days_ago=20)
        progress(ada, started, "Broca", ProgressStatus.IN_PROGRESS, minutes_ago=5)

        assert ordered_slugs(get_enrollments(client)) == ["started", "new", "old"]

    def test_ignores_other_learners_activity(self, client, ada, signed_in):
        grace = User.objects.create_user(email="grace@example.com")
        foundations = make_course_with_lessons("foundations")
        syntax = make_course_with_lessons("syntax")
        enroll(ada, foundations, days_ago=1)
        enroll(ada, syntax, days_ago=2)
        enroll(grace, syntax)
        progress(grace, syntax, "Intro", ProgressStatus.IN_PROGRESS, minutes_ago=5)

        assert ordered_slugs(get_enrollments(client)) == ["foundations", "syntax"]


class TestProgress:
    def test_last_activity_is_the_latest_progress_update(self, client, ada, signed_in):
        course = make_course_with_lessons("foundations")
        enroll(ada, course)
        progress(ada, course, "Intro", ProgressStatus.COMPLETED, minutes_ago=30)
        latest = progress(ada, course, "Broca", ProgressStatus.IN_PROGRESS, minutes_ago=5)

        item = item_for(client, "foundations")

        assert item["last_activity_at"] == latest.isoformat().replace("+00:00", "Z")

    def test_last_activity_is_null_with_no_progress(self, client, ada, signed_in):
        enroll(ada, make_course_with_lessons("foundations"))

        assert item_for(client, "foundations")["last_activity_at"] is None

    def test_last_activity_ignores_other_courses(self, client, ada, signed_in):
        foundations = make_course_with_lessons("foundations")
        syntax = make_course_with_lessons("syntax")
        enroll(ada, foundations)
        enroll(ada, syntax)
        progress(ada, syntax, "Intro", ProgressStatus.IN_PROGRESS, minutes_ago=5)

        assert item_for(client, "foundations")["last_activity_at"] is None

    def test_counts_completed_and_total_lessons(self, client, ada, signed_in):
        course = make_course_with_lessons("foundations")
        enroll(ada, course)
        progress(ada, course, "Intro", ProgressStatus.COMPLETED, minutes_ago=30)
        progress(ada, course, "Broca", ProgressStatus.IN_PROGRESS, minutes_ago=5)

        item = item_for(client, "foundations")

        assert (item["completed_lesson_count"], item["lesson_count"]) == (1, 3)


class TestContinue:
    def continue_title(self, client, slug):
        item = item_for(client, slug)
        assert (
            Lesson.objects.get(pk=item["continue_lesson_id"]).title == item["continue_lesson_title"]
        )
        return item["continue_lesson_title"]

    def test_with_no_progress_is_the_first_lesson(self, client, ada, signed_in):
        enroll(ada, make_course_with_lessons("foundations"))

        assert self.continue_title(client, "foundations") == "Intro"

    def test_is_the_latest_lesson_when_it_is_in_progress(self, client, ada, signed_in):
        course = make_course_with_lessons("foundations")
        enroll(ada, course)
        progress(ada, course, "Intro", ProgressStatus.COMPLETED, minutes_ago=30)
        progress(ada, course, "Wernicke", ProgressStatus.IN_PROGRESS, minutes_ago=5)

        assert self.continue_title(client, "foundations") == "Wernicke"

    def test_is_the_next_lesson_when_the_latest_is_complete(self, client, ada, signed_in):
        course = make_course_with_lessons("foundations")
        enroll(ada, course)
        progress(ada, course, "Intro", ProgressStatus.COMPLETED, minutes_ago=5)

        assert self.continue_title(client, "foundations") == "Broca"

    def test_is_the_latest_lesson_when_every_lesson_is_complete(self, client, ada, signed_in):
        course = make_course_with_lessons("foundations")
        enroll(ada, course)
        progress(ada, course, "Wernicke", ProgressStatus.COMPLETED, minutes_ago=30)
        progress(ada, course, "Intro", ProgressStatus.COMPLETED, minutes_ago=5)
        progress(ada, course, "Broca", ProgressStatus.COMPLETED, minutes_ago=10)

        assert self.continue_title(client, "foundations") == "Intro"

    def test_is_worked_out_per_course(self, client, ada, signed_in):
        foundations = make_course_with_lessons("foundations")
        syntax = make_course_with_lessons("syntax")
        enroll(ada, foundations)
        enroll(ada, syntax)
        progress(ada, foundations, "Broca", ProgressStatus.IN_PROGRESS, minutes_ago=30)
        progress(ada, syntax, "Wernicke", ProgressStatus.IN_PROGRESS, minutes_ago=5)

        assert self.continue_title(client, "foundations") == "Broca"
        assert self.continue_title(client, "syntax") == "Wernicke"

    def test_matches_the_continue_endpoint(self, client, ada, signed_in):
        course = make_course_with_lessons("foundations")
        enroll(ada, course)
        progress(ada, course, "Broca", ProgressStatus.COMPLETED, minutes_ago=5)

        continue_response = client.get(
            reverse("learn-continue", kwargs={"slug": "foundations"}),
            headers={"Authorization": "Bearer stub"},
        )

        assert (
            item_for(client, "foundations")["continue_lesson_id"]
            == continue_response.json()["lesson_id"]
        )

    def test_is_null_for_a_course_with_no_lessons(self, client, ada, signed_in):
        enroll(ada, make_course("empty", status=CourseStatus.DRAFT))

        item = item_for(client, "empty")

        assert item["continue_lesson_id"] is None
        assert item["continue_lesson_title"] is None
        assert (item["completed_lesson_count"], item["lesson_count"]) == (0, 0)
