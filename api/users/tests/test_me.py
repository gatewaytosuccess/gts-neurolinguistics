"""``GET /api/users/me`` -- what the frontend reads, and what it must not."""

import pytest
from django.urls import reverse

from users.authentication import ClerkAuthentication
from users.models import Role, User, UserStatus

pytestmark = pytest.mark.django_db


@pytest.fixture
def clerk_session(monkeypatch):
    """Stand in for a verified Clerk session token.

    Only JWKS verification is stubbed; everything downstream of it -- the
    just-in-time provisioning, the status check -- runs for real.
    """

    def use(**claims):
        monkeypatch.setattr(
            ClerkAuthentication,
            "decode_token",
            lambda self, token: {"sub": "user_2abcDEF", **claims},
        )

    return use


def get_me(client):
    return client.get(reverse("user-me"), headers={"Authorization": "Bearer stub-token"})


class TestAccess:
    def test_rejects_a_request_with_no_token(self, client):
        assert client.get(reverse("user-me")).status_code == 401

    def test_rejects_a_suspended_account(self, client, clerk_session, make_user):
        make_user(
            email="ada@example.com",
            clerk_user_id="user_2abcDEF",
            status=UserStatus.SUSPENDED,
        )
        clerk_session()
        assert get_me(client).status_code == 401

    def test_rejects_a_deleted_account(self, client, clerk_session, make_user):
        make_user(
            email="ada@example.com",
            clerk_user_id="user_2abcDEF",
            status=UserStatus.DELETED,
        )
        clerk_session()
        assert get_me(client).status_code == 401


class TestPayload:
    def test_returns_the_account(self, client, clerk_session, make_user):
        make_user(email="ada@example.com", clerk_user_id="user_2abcDEF", name="Ada")
        clerk_session()

        body = get_me(client).json()

        assert body["email"] == "ada@example.com"
        assert body["name"] == "Ada"
        assert body["role"] == Role.LEARNER

    @pytest.mark.parametrize(
        "field", ["status", "suspension_reason", "is_staff", "is_superuser", "password"]
    )
    def test_does_not_leak(self, client, clerk_session, make_user, field):
        make_user(email="ada@example.com", clerk_user_id="user_2abcDEF")
        clerk_session()
        assert field not in get_me(client).json()

    def test_is_read_only(self, client, clerk_session, make_user):
        make_user(email="ada@example.com", clerk_user_id="user_2abcDEF", name="Ada")
        clerk_session()

        response = client.patch(
            reverse("user-me"),
            data={"name": "Someone Else"},
            content_type="application/json",
            headers={"Authorization": "Bearer stub-token"},
        )

        assert response.status_code == 405, "Clerk owns the profile; edits go through Clerk"
        assert User.objects.get(clerk_user_id="user_2abcDEF").name == "Ada"


class TestProvisioningOnFirstCall:
    def test_creates_the_row_when_the_webhook_has_not_landed_yet(self, client, clerk_session):
        clerk_session(email="ada@example.com", name="Ada Lovelace")

        body = get_me(client).json()

        assert body["email"] == "ada@example.com"
        assert User.objects.get(clerk_user_id="user_2abcDEF").name == "Ada Lovelace"

    def test_cannot_provision_without_an_email_claim(self, client, clerk_session):
        clerk_session()
        assert get_me(client).status_code == 401
        assert not User.objects.exists()

    def test_will_not_hand_over_a_banned_account(self, client, clerk_session, make_user):
        make_user(email="ada@example.com", status=UserStatus.BANNED)
        clerk_session(email="ada@example.com")

        assert get_me(client).status_code == 401
        assert User.objects.get(email="ada@example.com").clerk_user_id is None
