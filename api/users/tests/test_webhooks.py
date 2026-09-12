import base64
import json
from datetime import datetime, timezone

import pytest
from django.urls import reverse
from svix.webhooks import Webhook

from users.models import User, UserStatus

pytestmark = pytest.mark.django_db

SECRET = "whsec_" + base64.b64encode(b"a-test-signing-secret-32-bytes!!").decode()


@pytest.fixture(autouse=True)
def signing_secret(settings):
    settings.CLERK_WEBHOOK_SIGNING_SECRET = SECRET
    return SECRET


@pytest.fixture
def post_event(client):
    """POST a Clerk event with a genuine Svix signature over the exact body."""

    def send(event_type, data, *, secret=SECRET, msg_id="msg_test"):
        body = json.dumps({"type": event_type, "data": data})
        timestamp = datetime.now(tz=timezone.utc)
        signature = Webhook(secret).sign(msg_id, timestamp, body)
        return client.post(
            reverse("clerk-webhook"),
            data=body,
            content_type="application/json",
            headers={
                "svix-id": msg_id,
                "svix-timestamp": str(int(timestamp.timestamp())),
                "svix-signature": signature,
            },
        )

    return send


class TestSignatureVerification:
    def test_rejects_an_unsigned_request(self, client, clerk_payload):
        response = client.post(
            reverse("clerk-webhook"),
            data=json.dumps({"type": "user.created", "data": clerk_payload()}),
            content_type="application/json",
        )
        assert response.status_code == 400
        assert not User.objects.exists()

    def test_rejects_a_signature_from_the_wrong_secret(self, post_event, clerk_payload):
        other = "whsec_" + base64.b64encode(b"a-different-secret-32-bytes-long").decode()
        response = post_event("user.created", clerk_payload(), secret=other)
        assert response.status_code == 400
        assert not User.objects.exists()

    def test_rejects_a_body_that_was_tampered_with(self, client, clerk_payload):
        body = json.dumps({"type": "user.created", "data": clerk_payload()})
        timestamp = datetime.now(tz=timezone.utc)
        signature = Webhook(SECRET).sign("msg_test", timestamp, body)
        response = client.post(
            reverse("clerk-webhook"),
            data=body.replace("ada@example.com", "attacker@example.com"),
            content_type="application/json",
            headers={
                "svix-id": "msg_test",
                "svix-timestamp": str(int(timestamp.timestamp())),
                "svix-signature": signature,
            },
        )
        assert response.status_code == 400
        assert not User.objects.exists()

    def test_refuses_to_run_at_all_without_a_configured_secret(
        self, settings, post_event, clerk_payload
    ):
        settings.CLERK_WEBHOOK_SIGNING_SECRET = ""
        assert post_event("user.created", clerk_payload()).status_code == 503


class TestUserCreated:
    def test_mirrors_the_new_user(self, post_event, clerk_payload):
        assert post_event("user.created", clerk_payload()).status_code == 200
        user = User.objects.get(clerk_user_id="user_2abcDEF")
        assert user.email == "ada@example.com"
        assert user.name == "Ada Lovelace"
        assert user.avatar_url == "https://img.clerk.com/ada.png"
        assert user.status == UserStatus.ACTIVE

    def test_redelivery_does_not_duplicate(self, post_event, clerk_payload):
        post_event("user.created", clerk_payload())
        post_event("user.created", clerk_payload())
        assert User.objects.count() == 1


class TestUserUpdated:
    def test_follows_a_name_and_email_change(self, post_event, clerk_payload):
        post_event("user.created", clerk_payload())
        post_event(
            "user.updated",
            clerk_payload(email="ada@newmail.com", last_name="Byron"),
        )
        user = User.objects.get(clerk_user_id="user_2abcDEF")
        assert (user.email, user.name) == ("ada@newmail.com", "Ada Byron")

    def test_an_email_collision_is_acknowledged_rather_than_retried_forever(
        self, post_event, clerk_payload, make_user
    ):
        make_user(email="taken@example.com", clerk_user_id="user_someone_else")
        post_event("user.created", clerk_payload())

        response = post_event("user.updated", clerk_payload(email="taken@example.com"))

        assert response.status_code == 200, "a 4xx/5xx would have Svix retrying for days"
        assert response.json()["status"] == "conflict"
        assert User.objects.get(clerk_user_id="user_2abcDEF").email == "ada@example.com"


class TestUserDeleted:
    def test_keeps_the_row_and_releases_the_clerk_id(self, post_event, clerk_payload):
        post_event("user.created", clerk_payload())
        assert post_event("user.deleted", {"id": "user_2abcDEF", "deleted": True}).status_code == 200

        user = User.objects.get(email="ada@example.com")
        assert user.status == UserStatus.DELETED
        assert user.clerk_user_id is None

    def test_an_unknown_user_is_still_a_successful_delivery(self, post_event):
        response = post_event("user.deleted", {"id": "user_never_seen", "deleted": True})
        assert response.status_code == 200
        assert response.json()["status"] == "unknown"


class TestOtherEvents:
    def test_an_unsubscribed_event_type_is_acknowledged_and_ignored(self, post_event):
        response = post_event("session.created", {"id": "sess_1"})
        assert response.status_code == 200
        assert response.json()["status"] == "ignored"
        assert not User.objects.exists()
