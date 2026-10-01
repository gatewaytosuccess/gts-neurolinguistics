import logging
import uuid

import pytest
from django.urls import reverse

from users.authentication import ClerkAuthentication
from users.models import Role, User, UserStatus

pytestmark = pytest.mark.django_db


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


def make_user(role=Role.LEARNER, status=UserStatus.ACTIVE, **fields):
    fields.setdefault("clerk_user_id", None if status == UserStatus.DELETED else "user_target")
    return User.objects.create_user(
        email="target@example.com", name="Ada Learner", role=role, status=status, **fields
    )


def patch_user(client, pk, data):
    return client.patch(
        reverse("admin-user-detail", args=[pk]),
        data,
        content_type="application/json",
        headers={"Authorization": "Bearer stub"},
    )


def change_role(client, pk, role):
    response = patch_user(client, pk, {"role": role})
    assert response.status_code == 200, response.json()
    return response.json()


def refusal(client, pk, data):
    response = patch_user(client, pk, data)
    assert response.status_code == 400
    return response.json()


class TestAccess:
    def test_rejects_a_request_with_no_token(self, client):
        target = make_user()
        response = client.patch(
            reverse("admin-user-detail", args=[target.pk]),
            {"role": Role.ADMIN},
            content_type="application/json",
        )
        assert response.status_code == 401

    @pytest.mark.parametrize("role", [Role.LEARNER, Role.INSTRUCTOR])
    def test_forbids_every_other_role(self, client, signed_in, role):
        User.objects.create_user(email="admin@example.com", clerk_user_id="user_admin", role=role)
        target = make_user()

        assert patch_user(client, target.pk, {"role": Role.ADMIN}).status_code == 403

        target.refresh_from_db()
        assert target.role == Role.LEARNER

    def test_an_unknown_id_is_a_404(self, client, admin):
        assert patch_user(client, uuid.uuid4(), {"role": Role.ADMIN}).status_code == 404

    def test_put_is_not_allowed(self, client, admin):
        target = make_user()
        response = client.put(
            reverse("admin-user-detail", args=[target.pk]),
            {"role": Role.ADMIN},
            content_type="application/json",
            headers={"Authorization": "Bearer stub"},
        )
        assert response.status_code == 405


class TestChanges:
    def test_promotes_a_learner_and_answers_with_the_detail_payload(self, client, admin):
        target = make_user()

        body = change_role(client, target.pk, Role.ADMIN)

        assert body["id"] == str(target.pk)
        assert body["role"] == Role.ADMIN
        assert {"status", "has_clerk_identity", "orders", "reviews"} <= set(body)
        target.refresh_from_db()
        assert target.role == Role.ADMIN

    def test_demotes_an_admin(self, client, admin):
        target = make_user(role=Role.ADMIN)

        assert change_role(client, target.pk, Role.LEARNER)["role"] == Role.LEARNER

        target.refresh_from_db()
        assert target.role == Role.LEARNER

    @pytest.mark.parametrize("new_role", [Role.LEARNER, Role.ADMIN])
    def test_moves_an_instructor_off_the_role(self, client, admin, new_role):
        target = make_user(role=Role.INSTRUCTOR)

        assert change_role(client, target.pk, new_role)["role"] == new_role

        target.refresh_from_db()
        assert target.role == new_role

    @pytest.mark.parametrize("status", [UserStatus.SUSPENDED, UserStatus.DELETED])
    def test_demotes_an_admin_who_isnt_active(self, client, admin, status):
        target = make_user(role=Role.ADMIN, status=status)

        assert change_role(client, target.pk, Role.LEARNER)["role"] == Role.LEARNER

    def test_the_promoted_user_passes_the_admin_check(self, client, admin, monkeypatch):
        target = make_user()
        change_role(client, target.pk, Role.ADMIN)

        monkeypatch.setattr(
            ClerkAuthentication, "decode_token", lambda self, token: {"sub": "user_target"}
        )
        response = client.get(reverse("admin-user-list"), headers={"Authorization": "Bearer stub"})
        assert response.status_code == 200

    def test_logs_the_actor_target_and_both_roles(self, client, admin, caplog):
        target = make_user()

        with caplog.at_level(logging.INFO, logger="users.views"):
            change_role(client, target.pk, Role.ADMIN)

        [record] = [r for r in caplog.records if r.name == "users.views"]
        message = record.getMessage()
        assert str(admin.pk) in message
        assert str(target.pk) in message
        assert "from learner to admin" in message


class TestRefusals:
    def test_refuses_instructor_as_a_target(self, client, admin):
        target = make_user()

        body = refusal(client, target.pk, {"role": Role.INSTRUCTOR})

        assert body["role"] == ["Nobody can be made an instructor. Choose learner or admin."]
        target.refresh_from_db()
        assert target.role == Role.LEARNER

    def test_refuses_an_instructor_staying_one(self, client, admin):
        target = make_user(role=Role.INSTRUCTOR)

        assert "role" in refusal(client, target.pk, {"role": Role.INSTRUCTOR})

    def test_refuses_an_unknown_role(self, client, admin):
        target = make_user()

        body = refusal(client, target.pk, {"role": "superuser"})

        assert body["role"] == ['"superuser" is not a valid choice.']

    def test_refuses_a_missing_role(self, client, admin):
        target = make_user()

        assert refusal(client, target.pk, {})["role"] == ["This field is required."]

    @pytest.mark.parametrize("new_role", [Role.LEARNER, Role.ADMIN])
    def test_refuses_a_change_to_your_own_role(self, client, admin, new_role):
        body = refusal(client, admin.pk, {"role": new_role})

        assert body["non_field_errors"] == ["You can't change your own role."]
        admin.refresh_from_db()
        assert admin.role == Role.ADMIN

    @pytest.mark.parametrize("status", [UserStatus.SUSPENDED, UserStatus.DELETED])
    def test_refuses_to_promote_a_user_who_isnt_active(self, client, admin, status):
        target = make_user(status=status)

        body = refusal(client, target.pk, {"role": Role.ADMIN})

        assert body["non_field_errors"] == [
            f"Only an active user can be made an admin. This user is {status}."
        ]
        target.refresh_from_db()
        assert target.role == Role.LEARNER

    def test_no_other_field_is_writable(self, client, admin):
        target = make_user()
        before = User.objects.values().get(pk=target.pk)

        response = patch_user(
            client,
            target.pk,
            {
                "role": Role.ADMIN,
                "email": "hijack@example.com",
                "name": "Someone Else",
                "avatar_url": "https://img.example.com/else.png",
                "status": UserStatus.SUSPENDED,
                "suspension_reason": "Written through PATCH",
                "clerk_user_id": "user_else",
                "is_staff": True,
                "is_superuser": True,
                "created_at": "2000-01-01T00:00:00Z",
            },
        )

        assert response.status_code == 200
        after = User.objects.values().get(pk=target.pk)
        assert after["role"] == Role.ADMIN
        unchanged = set(before) - {"role", "updated_at"}
        assert {f: after[f] for f in unchanged} == {f: before[f] for f in unchanged}
