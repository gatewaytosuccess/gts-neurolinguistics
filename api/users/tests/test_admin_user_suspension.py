import logging
import uuid

import pytest
from django.urls import reverse

from courses.models import Course, CourseStatus
from enrollments.models import Enrollment, EnrollmentSource, EnrollmentStatus
from users.authentication import ClerkAuthentication
from users.models import Role, User, UserStatus
from users.sync import MirrorConflict, mirror_user

pytestmark = pytest.mark.django_db

SELF_REFUSAL = "You can't change your own role or status."


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


@pytest.fixture
def deleted():
    return User.objects.create_user(email="gone@example.com", status=UserStatus.DELETED)


def suspend(client, pk, reason="Chargeback fraud"):
    body = {} if reason is None else {"reason": reason}
    return client.post(
        reverse("admin-user-suspend", args=[pk]),
        body,
        content_type="application/json",
        headers={"Authorization": "Bearer stub"},
    )


def reinstate(client, pk):
    return client.post(
        reverse("admin-user-reinstate", args=[pk]), headers={"Authorization": "Bearer stub"}
    )


def refusal(response):
    assert response.status_code == 400, response.json()
    return response.json()["non_field_errors"]


class TestAccess:
    @pytest.mark.parametrize("url_name", ["admin-user-suspend", "admin-user-reinstate"])
    def test_rejects_a_request_with_no_token(self, client, learner, url_name):
        assert client.post(reverse(url_name, args=[learner.pk])).status_code == 401

    @pytest.mark.parametrize("role", [Role.LEARNER, Role.INSTRUCTOR])
    def test_forbids_every_other_role(self, client, signed_in, learner, role):
        User.objects.create_user(email="admin@example.com", clerk_user_id="user_admin", role=role)
        learner.suspend("Chargeback fraud")
        other = User.objects.create_user(email="other@example.com", clerk_user_id="user_other")

        assert suspend(client, other.pk).status_code == 403
        assert reinstate(client, learner.pk).status_code == 403
        other.refresh_from_db()
        learner.refresh_from_db()
        assert other.status == UserStatus.ACTIVE
        assert learner.status == UserStatus.SUSPENDED

    def test_an_unknown_id_is_a_404(self, client, admin):
        assert suspend(client, uuid.uuid4()).status_code == 404
        assert reinstate(client, uuid.uuid4()).status_code == 404


class TestSuspend:
    def test_suspends_an_active_user_and_returns_the_detail_payload(self, client, admin, learner):
        response = suspend(client, learner.pk, reason="  Chargeback fraud  ")

        assert response.status_code == 200, response.json()
        body = response.json()
        assert body["id"] == str(learner.pk)
        assert body["status"] == UserStatus.SUSPENDED
        assert body["suspended_at"] is not None
        assert body["suspension_reason"] == "Chargeback fraud"
        assert body["orders"] == []
        assert body["reviews"] == []
        learner.refresh_from_db()
        assert learner.status == UserStatus.SUSPENDED
        assert learner.suspension_reason == "Chargeback fraud"

    def test_the_suspended_user_is_refused_by_the_api(self, client, admin, learner, monkeypatch):
        suspend(client, learner.pk)

        monkeypatch.setattr(
            ClerkAuthentication, "decode_token", lambda self, token: {"sub": "user_learner"}
        )
        response = client.get(reverse("user-me"), headers={"Authorization": "Bearer stub"})

        assert response.status_code == 401
        assert response.json()["code"] == "account_suspended"

    @pytest.mark.parametrize("reason", [None, "", "   "])
    def test_a_missing_or_blank_reason_is_refused(self, client, admin, learner, reason):
        response = suspend(client, learner.pk, reason=reason)

        assert response.status_code == 400
        assert response.json()["reason"] == ["Give a reason for suspending this user."]
        learner.refresh_from_db()
        assert learner.status == UserStatus.ACTIVE

    def test_a_reason_over_500_characters_is_refused(self, client, admin, learner):
        response = suspend(client, learner.pk, reason="x" * 501)

        assert response.status_code == 400
        assert "reason" in response.json()
        learner.refresh_from_db()
        assert learner.status == UserStatus.ACTIVE

    def test_a_reason_of_500_characters_is_accepted(self, client, admin, learner):
        response = suspend(client, learner.pk, reason="x" * 500)

        assert response.status_code == 200, response.json()
        assert response.json()["suspension_reason"] == "x" * 500

    def test_the_requester_cant_suspend_themselves(self, client, admin):
        assert refusal(suspend(client, admin.pk)) == [SELF_REFUSAL]
        admin.refresh_from_db()
        assert admin.status == UserStatus.ACTIVE

    def test_an_admin_cant_be_suspended(self, client, admin):
        other_admin = User.objects.create_user(
            email="second@example.com", clerk_user_id="user_second", role=Role.ADMIN
        )

        assert refusal(suspend(client, other_admin.pk)) == [
            "An admin can't be suspended. Demote them first."
        ]
        other_admin.refresh_from_db()
        assert other_admin.status == UserStatus.ACTIVE

    def test_an_already_suspended_user_is_refused_and_keeps_its_suspension(
        self, client, admin, learner
    ):
        learner.suspend("Chargeback fraud")
        suspended_at = learner.suspended_at

        assert refusal(suspend(client, learner.pk, reason="Something else")) == [
            "This user is already suspended."
        ]
        learner.refresh_from_db()
        assert learner.suspended_at == suspended_at
        assert learner.suspension_reason == "Chargeback fraud"

    def test_a_deleted_user_can_be_suspended_and_then_cant_sign_up_again(
        self, client, admin, deleted
    ):
        response = suspend(client, deleted.pk)

        assert response.status_code == 200, response.json()
        assert response.json()["status"] == UserStatus.SUSPENDED
        with pytest.raises(MirrorConflict):
            mirror_user(clerk_user_id="user_new", email="gone@example.com")
        deleted.refresh_from_db()
        assert deleted.status == UserStatus.SUSPENDED
        assert deleted.clerk_user_id is None

    def test_logs_the_actor_target_and_reason(self, client, admin, learner, caplog):
        with caplog.at_level(logging.INFO, logger="users.views"):
            suspend(client, learner.pk)

        assert f"Admin {admin.id} suspended user {learner.id}: Chargeback fraud" in caplog.text


class TestReinstate:
    def test_a_user_with_a_clerk_identity_becomes_active(self, client, admin, learner):
        learner.suspend("Chargeback fraud")

        response = reinstate(client, learner.pk)

        assert response.status_code == 200, response.json()
        body = response.json()
        assert body["id"] == str(learner.pk)
        assert body["status"] == UserStatus.ACTIVE
        assert body["suspended_at"] is None
        assert body["suspension_reason"] == ""
        assert body["has_clerk_identity"] is True

    def test_a_user_without_a_clerk_identity_returns_to_deleted_and_can_sign_up_again(
        self, client, admin, deleted
    ):
        deleted.suspend("Chargeback fraud")

        response = reinstate(client, deleted.pk)

        assert response.status_code == 200, response.json()
        assert response.json()["status"] == UserStatus.DELETED
        assert response.json()["has_clerk_identity"] is False
        resurrected = mirror_user(clerk_user_id="user_new", email="gone@example.com")
        assert resurrected.pk == deleted.pk
        assert resurrected.status == UserStatus.ACTIVE

    @pytest.mark.parametrize("status", [UserStatus.ACTIVE, UserStatus.DELETED])
    def test_a_user_who_isnt_suspended_is_refused(self, client, admin, status):
        user = User.objects.create_user(email="other@example.com", status=status)

        assert refusal(reinstate(client, user.pk)) == ["This user isn't suspended."]
        user.refresh_from_db()
        assert user.status == status

    def test_the_requester_cant_reinstate_themselves(self, client, admin):
        assert refusal(reinstate(client, admin.pk)) == [SELF_REFUSAL]

    def test_logs_the_actor_target_outcome_and_cleared_reason(self, client, admin, learner, caplog):
        learner.suspend("Chargeback fraud")

        with caplog.at_level(logging.INFO, logger="users.views"):
            reinstate(client, learner.pk)

        assert (
            f"Admin {admin.id} reinstated user {learner.id} as active; "
            "they were suspended for: Chargeback fraud"
        ) in caplog.text


def test_suspending_and_reinstating_leave_enrollments_untouched(client, admin, learner):
    for slug, source, status in [
        ("intro", EnrollmentSource.COMP, EnrollmentStatus.ACTIVE),
        ("advanced", EnrollmentSource.MANUAL, EnrollmentStatus.REVOKED),
    ]:
        Enrollment.objects.create(
            user=learner,
            course=Course.objects.create(
                slug=slug, title=slug.title(), price_cents=12900, status=CourseStatus.PUBLISHED
            ),
            source=source,
            status=status,
        )

    def enrollments():
        return list(Enrollment.objects.filter(user=learner).order_by("pk").values())

    before = enrollments()

    assert suspend(client, learner.pk).status_code == 200
    assert enrollments() == before

    assert reinstate(client, learner.pk).status_code == 200
    assert enrollments() == before
