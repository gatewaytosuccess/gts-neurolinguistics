import logging
import uuid
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from commerce.models import Order, OrderStatus
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
        ClerkAuthentication, "decode_token", lambda self, token: {"sub": "user_admin"}
    )


@pytest.fixture
def admin(signed_in):
    return User.objects.create_user(
        email="admin@example.com", clerk_user_id="user_admin", role=Role.ADMIN
    )


@pytest.fixture
def learner():
    return User.objects.create_user(email="learner@example.com", clerk_user_id="user_learner")


def make_course(slug, status=CourseStatus.PUBLISHED):
    return Course.objects.create(slug=slug, title=slug.title(), price_cents=12900, status=status)


def add_lessons(course, count):
    module = Module.objects.create(
        course=course, title="Module", position=course.modules.count() + 1
    )
    return [
        Lesson.objects.create(module=module, title=f"Lesson {i}", position=i)
        for i in range(1, count + 1)
    ]


def place_order(user):
    return Order.objects.create(
        user=user, status=OrderStatus.PAID, subtotal_cents=12900, total_cents=12900
    )


def enroll(user, course, **fields):
    fields.setdefault("source", EnrollmentSource.MANUAL)
    return Enrollment.objects.create(user=user, course=course, **fields)


def list_enrollments(client, pk):
    return client.get(reverse("admin-user-enrollments", args=[pk]), headers=AUTH)


def grant(client, pk, course_id, source=EnrollmentSource.COMP):
    return client.post(
        reverse("admin-user-enrollments", args=[pk]),
        {"course_id": str(course_id), "source": source},
        content_type="application/json",
        headers=AUTH,
    )


def revoke(client, pk):
    return client.post(reverse("admin-enrollment-revoke", args=[pk]), headers=AUTH)


def restore(client, pk):
    return client.post(reverse("admin-enrollment-restore", args=[pk]), headers=AUTH)


def refusal(response):
    assert response.status_code == 400, response.json()
    return response.json()["non_field_errors"]


class TestAccess:
    @pytest.mark.parametrize("role", [Role.LEARNER, Role.INSTRUCTOR])
    def test_forbids_every_other_role(self, client, signed_in, learner, role):
        User.objects.create_user(email="admin@example.com", clerk_user_id="user_admin", role=role)
        course = make_course("foundations")
        enrollment = enroll(learner, make_course("syntax"))

        assert list_enrollments(client, learner.pk).status_code == 403
        assert grant(client, learner.pk, course.pk).status_code == 403
        assert revoke(client, enrollment.pk).status_code == 403
        enrollment.status = EnrollmentStatus.REVOKED
        enrollment.save()
        assert restore(client, enrollment.pk).status_code == 403
        assert not Enrollment.objects.filter(course=course).exists()
        enrollment.refresh_from_db()
        assert enrollment.status == EnrollmentStatus.REVOKED

    def test_rejects_a_request_with_no_token(self, client, learner):
        assert client.get(reverse("admin-user-enrollments", args=[learner.pk])).status_code == 401

    def test_an_unknown_id_is_a_404(self, client, admin):
        assert list_enrollments(client, uuid.uuid4()).status_code == 404
        assert grant(client, uuid.uuid4(), make_course("foundations").pk).status_code == 404
        assert revoke(client, uuid.uuid4()).status_code == 404
        assert restore(client, uuid.uuid4()).status_code == 404


class TestList:
    def test_puts_active_first_then_newest(self, client, admin, learner):
        now = timezone.now()
        for slug, days_ago, status in [
            ("old-active", 3, EnrollmentStatus.ACTIVE),
            ("new-revoked", 0, EnrollmentStatus.REVOKED),
            ("new-active", 1, EnrollmentStatus.ACTIVE),
            ("old-revoked", 2, EnrollmentStatus.REVOKED),
        ]:
            enrollment = enroll(learner, make_course(slug), status=status)
            Enrollment.objects.filter(pk=enrollment.pk).update(
                enrolled_at=now - timedelta(days=days_ago)
            )

        response = list_enrollments(client, learner.pk)

        assert response.status_code == 200
        assert [row["course"]["slug"] for row in response.json()] == [
            "new-active",
            "old-active",
            "new-revoked",
            "old-revoked",
        ]

    def test_returns_only_that_users_enrollments_unpaginated(
        self, client, admin, learner, settings
    ):
        other = User.objects.create_user(email="other@example.com")
        enroll(other, make_course("theirs"))
        for i in range(settings.REST_FRAMEWORK["PAGE_SIZE"] + 1):
            enroll(learner, make_course(f"course-{i}"))

        body = list_enrollments(client, learner.pk).json()

        assert isinstance(body, list)
        assert len(body) == settings.REST_FRAMEWORK["PAGE_SIZE"] + 1
        assert "theirs" not in {row["course"]["slug"] for row in body}

    def test_returns_the_row_fields(self, client, admin, learner):
        course = make_course("unpublished", status=CourseStatus.DRAFT)
        order = place_order(learner)
        enrollment = enroll(learner, course, source=EnrollmentSource.PURCHASE, order=order)

        (row,) = list_enrollments(client, learner.pk).json()

        assert row["id"] == str(enrollment.pk)
        assert row["course"] == {
            "id": str(course.pk),
            "title": "Unpublished",
            "slug": "unpublished",
            "status": CourseStatus.DRAFT,
        }
        assert row["source"] == EnrollmentSource.PURCHASE
        assert row["status"] == EnrollmentStatus.ACTIVE
        assert row["order_id"] == str(order.pk)
        assert row["enrolled_at"]
        assert row["revoked_at"] is None

    def test_counts_current_lessons_and_only_this_users_completed_ones(
        self, client, admin, learner
    ):
        course = make_course("foundations")
        first, second, third = add_lessons(course, 3)
        add_lessons(course, 1)
        other = User.objects.create_user(email="other@example.com")
        for user, lesson, status in [
            (learner, first, ProgressStatus.COMPLETED),
            (learner, second, ProgressStatus.IN_PROGRESS),
            (other, second, ProgressStatus.COMPLETED),
            (other, third, ProgressStatus.COMPLETED),
        ]:
            LessonProgress.objects.create(user=user, lesson=lesson, status=status)
        enroll(learner, course)
        enroll(learner, make_course("empty"))

        rows = {row["course"]["slug"]: row for row in list_enrollments(client, learner.pk).json()}

        assert (
            rows["foundations"]["completed_lesson_count"],
            rows["foundations"]["lesson_count"],
        ) == (1, 4)
        assert (rows["empty"]["completed_lesson_count"], rows["empty"]["lesson_count"]) == (0, 0)

    def test_progress_on_another_courses_lessons_is_not_counted(self, client, admin, learner):
        course = make_course("foundations")
        add_lessons(course, 2)
        (elsewhere,) = add_lessons(make_course("syntax"), 1)
        LessonProgress.objects.create(
            user=learner, lesson=elsewhere, status=ProgressStatus.COMPLETED
        )
        enroll(learner, course)

        (row,) = list_enrollments(client, learner.pk).json()

        assert (row["completed_lesson_count"], row["lesson_count"]) == (0, 2)

    def test_does_not_query_per_enrollment(
        self, client, admin, learner, django_assert_max_num_queries
    ):
        for i in range(3):
            course = make_course(f"course-{i}")
            add_lessons(course, 2)
            enroll(learner, course)

        # The requester, the target user, and the enrollments.
        with django_assert_max_num_queries(3):
            list_enrollments(client, learner.pk)


class TestGrant:
    @pytest.mark.parametrize("source", [EnrollmentSource.MANUAL, EnrollmentSource.COMP])
    def test_grants_each_source(self, client, admin, learner, source):
        course = make_course("foundations")

        response = grant(client, learner.pk, course.pk, source=source)

        assert response.status_code == 201, response.json()
        enrollment = Enrollment.objects.get(user=learner, course=course)
        assert response.json()["id"] == str(enrollment.pk)
        assert response.json()["source"] == source
        assert response.json()["status"] == EnrollmentStatus.ACTIVE
        assert enrollment.source == source
        assert enrollment.order is None

    def test_grants_a_draft_course(self, client, admin, learner):
        course = make_course("unpublished", status=CourseStatus.DRAFT)

        response = grant(client, learner.pk, course.pk)

        assert response.status_code == 201, response.json()
        assert response.json()["course"]["status"] == CourseStatus.DRAFT
        assert Enrollment.objects.filter(user=learner, course=course).exists()

    def test_the_granted_course_reaches_the_learners_own_list(
        self, client, admin, learner, monkeypatch
    ):
        course = make_course("foundations")
        grant(client, learner.pk, course.pk)

        monkeypatch.setattr(
            ClerkAuthentication, "decode_token", lambda self, token: {"sub": "user_learner"}
        )
        response = client.get(reverse("user-me-enrollments"), headers=AUTH)

        assert [row["course_slug"] for row in response.json()] == ["foundations"]

    @pytest.mark.parametrize("status", [UserStatus.SUSPENDED, UserStatus.DELETED])
    def test_grants_to_any_account_status(self, client, admin, learner, status):
        User.objects.filter(pk=learner.pk).update(status=status)

        assert grant(client, learner.pk, make_course("foundations").pk).status_code == 201

    def test_refuses_an_active_duplicate(self, client, admin, learner):
        course = make_course("foundations")
        enroll(learner, course)

        assert refusal(grant(client, learner.pk, course.pk)) == [
            "This user is already enrolled in this course."
        ]
        assert Enrollment.objects.filter(user=learner).count() == 1

    def test_refuses_a_revoked_duplicate(self, client, admin, learner):
        course = make_course("foundations")
        enrollment = enroll(learner, course, status=EnrollmentStatus.REVOKED)

        (message,) = refusal(grant(client, learner.pk, course.pk))

        assert "Restore the existing enrollment instead" in message
        enrollment.refresh_from_db()
        assert enrollment.status == EnrollmentStatus.REVOKED

    def test_refuses_an_unknown_course(self, client, admin, learner):
        response = grant(client, learner.pk, uuid.uuid4())

        assert response.status_code == 400
        assert response.json()["course_id"] == ["No course has this id."]
        assert not Enrollment.objects.exists()

    @pytest.mark.parametrize("source", [EnrollmentSource.PURCHASE, "gift", ""])
    def test_refuses_an_invalid_source(self, client, admin, learner, source):
        response = grant(client, learner.pk, make_course("foundations").pk, source=source)

        assert response.status_code == 400
        assert "source" in response.json()
        assert not Enrollment.objects.exists()

    def test_logs_the_actor_target_course_and_source(self, client, admin, learner, caplog):
        course = make_course("foundations")

        with caplog.at_level(logging.INFO, logger="enrollments.views"):
            grant(client, learner.pk, course.pk, source=EnrollmentSource.COMP)

        assert f"Admin {admin.pk} granted user {learner.pk} course {course.pk} as comp." in (
            caplog.text
        )


class TestRevoke:
    def test_revokes_an_active_enrollment(self, client, admin, learner):
        enrollment = enroll(learner, make_course("foundations"))

        response = revoke(client, enrollment.pk)

        assert response.status_code == 200, response.json()
        assert response.json()["status"] == EnrollmentStatus.REVOKED
        assert response.json()["revoked_at"]
        enrollment.refresh_from_db()
        assert enrollment.status == EnrollmentStatus.REVOKED
        assert enrollment.revoked_at is not None

    def test_a_revoked_course_leaves_the_learners_own_list(
        self, client, admin, learner, monkeypatch
    ):
        enrollment = enroll(learner, make_course("foundations"))
        revoke(client, enrollment.pk)

        monkeypatch.setattr(
            ClerkAuthentication, "decode_token", lambda self, token: {"sub": "user_learner"}
        )
        assert client.get(reverse("user-me-enrollments"), headers=AUTH).json() == []

    def test_refuses_an_enrollment_already_revoked(self, client, admin, learner):
        revoked_at = timezone.now() - timedelta(days=1)
        enrollment = enroll(
            learner,
            make_course("foundations"),
            status=EnrollmentStatus.REVOKED,
            revoked_at=revoked_at,
        )

        assert refusal(revoke(client, enrollment.pk)) == ["This enrollment is already revoked."]
        enrollment.refresh_from_db()
        assert enrollment.revoked_at == revoked_at

    @pytest.mark.parametrize("status", [UserStatus.SUSPENDED, UserStatus.DELETED])
    def test_revokes_for_any_account_status(self, client, admin, learner, status):
        enrollment = enroll(learner, make_course("foundations"))
        User.objects.filter(pk=learner.pk).update(status=status)

        assert revoke(client, enrollment.pk).status_code == 200

    def test_logs_the_actor_target_and_course(self, client, admin, learner, caplog):
        course = make_course("foundations")
        enrollment = enroll(learner, course)

        with caplog.at_level(logging.INFO, logger="enrollments.views"):
            revoke(client, enrollment.pk)

        assert (
            f"Admin {admin.pk} revoked the enrollment of user {learner.pk} in course {course.pk}."
        ) in caplog.text


class TestRestore:
    def test_restores_with_the_original_source_order_and_date(self, client, admin, learner):
        order = place_order(learner)
        enrollment = enroll(
            learner, make_course("foundations"), source=EnrollmentSource.PURCHASE, order=order
        )
        enrolled_at = enrollment.enrolled_at
        revoke(client, enrollment.pk)

        response = restore(client, enrollment.pk)

        assert response.status_code == 200, response.json()
        body = response.json()
        assert body["status"] == EnrollmentStatus.ACTIVE
        assert body["revoked_at"] is None
        assert body["source"] == EnrollmentSource.PURCHASE
        assert body["order_id"] == str(order.pk)
        enrollment.refresh_from_db()
        assert enrollment.status == EnrollmentStatus.ACTIVE
        assert enrollment.revoked_at is None
        assert enrollment.source == EnrollmentSource.PURCHASE
        assert enrollment.order_id == order.pk
        assert enrollment.enrolled_at == enrolled_at

    def test_refuses_an_enrollment_already_active(self, client, admin, learner):
        enrollment = enroll(learner, make_course("foundations"))

        assert refusal(restore(client, enrollment.pk)) == ["This enrollment is already active."]

    @pytest.mark.parametrize("status", [UserStatus.SUSPENDED, UserStatus.DELETED])
    def test_restores_for_any_account_status(self, client, admin, learner, status):
        enrollment = enroll(learner, make_course("foundations"), status=EnrollmentStatus.REVOKED)
        User.objects.filter(pk=learner.pk).update(status=status)

        assert restore(client, enrollment.pk).status_code == 200

    def test_logs_the_actor_target_and_course(self, client, admin, learner, caplog):
        course = make_course("foundations")
        enrollment = enroll(learner, course, status=EnrollmentStatus.REVOKED)

        with caplog.at_level(logging.INFO, logger="enrollments.views"):
            restore(client, enrollment.pk)

        assert (
            f"Admin {admin.pk} restored the enrollment of user {learner.pk} in course {course.pk}."
        ) in caplog.text


def test_the_course_lists_enrolled_count_follows_grants_and_revokes(client, admin, learner):
    course = make_course("foundations")

    def enrolled_count():
        response = client.get(reverse("admin-course-list"), headers=AUTH)
        (row,) = response.json()["results"]
        return row["active_enrollment_count"]

    grant(client, learner.pk, course.pk)
    assert enrolled_count() == 1
    enrollment = Enrollment.objects.get()
    revoke(client, enrollment.pk)
    assert enrolled_count() == 0
    restore(client, enrollment.pk)
    assert enrolled_count() == 1
