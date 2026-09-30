import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from django.urls import reverse

from users import authentication
from users.authentication import ClerkAuthentication
from users.models import Role, User, UserStatus

pytestmark = pytest.mark.django_db


@pytest.fixture
def clerk_session(monkeypatch):
    """Stubs only token verification; provisioning and the status check run for real."""

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

    def test_rejects_a_suspended_account_with_a_code(self, client, clerk_session, make_user):
        make_user(
            email="ada@example.com",
            clerk_user_id="user_2abcDEF",
            status=UserStatus.SUSPENDED,
        )
        clerk_session()

        response = get_me(client)

        assert response.status_code == 401
        assert response.json()["code"] == "account_suspended"

    def test_rejects_a_deleted_account_without_the_suspended_code(
        self, client, clerk_session, make_user
    ):
        make_user(
            email="ada@example.com",
            clerk_user_id="user_2abcDEF",
            status=UserStatus.DELETED,
        )
        clerk_session()

        response = get_me(client)

        assert response.status_code == 401
        assert "code" not in response.json()


class TestBadTokens:
    """Real signature checks against a local key, with only the JWKS fetch stubbed."""

    @pytest.fixture
    def signing_key(self, monkeypatch, settings, make_user):
        settings.CLERK_ISSUER = ""
        settings.CLERK_AUTHORIZED_PARTIES = []
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        class Jwks:
            def get_signing_key_from_jwt(self, token):
                return jwt.PyJWK.from_dict(
                    jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key(), as_dict=True)
                )

        monkeypatch.setattr(authentication, "get_jwks_client", lambda: Jwks())
        make_user(email="ada@example.com", clerk_user_id="user_2abcDEF")
        return key

    def get_me_with(self, client, key, expires_in):
        token = jwt.encode(
            {"sub": "user_2abcDEF", "exp": int(time.time()) + expires_in}, key, algorithm="RS256"
        )
        return client.get(reverse("user-me"), headers={"Authorization": f"Bearer {token}"})

    def test_accepts_a_valid_token(self, client, signing_key):
        assert self.get_me_with(client, signing_key, expires_in=60).status_code == 200

    def test_an_expired_token_is_not_a_suspension(self, client, signing_key):
        response = self.get_me_with(client, signing_key, expires_in=-60)

        assert response.status_code == 401
        assert "code" not in response.json()

    def test_an_invalid_token_is_not_a_suspension(self, client, signing_key):
        forged = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        response = self.get_me_with(client, forged, expires_in=60)

        assert response.status_code == 401
        assert "code" not in response.json()


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

    def test_will_not_hand_over_a_suspended_account(self, client, clerk_session, make_user):
        make_user(email="ada@example.com", status=UserStatus.SUSPENDED)
        clerk_session(email="ada@example.com")

        assert get_me(client).status_code == 401
        assert User.objects.get(email="ada@example.com").clerk_user_id is None
