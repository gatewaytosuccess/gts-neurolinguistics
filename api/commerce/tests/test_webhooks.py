import json
import time

import pytest
import stripe
from django.urls import reverse

SECRET = "whsec_a-test-signing-secret"


@pytest.fixture(autouse=True)
def signing_secret(settings):
    settings.STRIPE_WEBHOOK_SECRET = SECRET
    return SECRET


def sign(body, *, secret=SECRET, timestamp=None):
    return stripe.WebhookSignature.generate_signature_header(body, secret, timestamp)


@pytest.fixture
def post_event(client):
    """POST a body with a genuine Stripe signature over it, unless ``signature`` is given."""

    def send(body, *, signature=None):
        headers = {"Stripe-Signature": sign(body) if signature is None else signature}
        return client.post(
            reverse("stripe-webhook"), data=body, content_type="application/json", headers=headers
        )

    return send


def event(event_type="checkout.session.completed"):
    return json.dumps(
        {"id": "evt_test", "object": "event", "type": event_type, "data": {"object": {}}}
    )


class TestSignatureVerification:
    def test_refuses_to_run_at_all_without_a_configured_secret(self, settings, post_event):
        settings.STRIPE_WEBHOOK_SECRET = ""
        assert post_event(event()).status_code == 503

    def test_rejects_an_unsigned_request(self, client):
        response = client.post(
            reverse("stripe-webhook"), data=event(), content_type="application/json"
        )
        assert response.status_code == 400

    def test_rejects_a_signature_from_the_wrong_secret(self, post_event):
        body = event()
        assert post_event(body, signature=sign(body, secret="whsec_other")).status_code == 400

    def test_rejects_a_body_that_was_tampered_with(self, post_event):
        signature = sign(event())
        assert post_event(event("charge.refunded"), signature=signature).status_code == 400

    def test_rejects_a_stale_signature(self, post_event):
        body = event()
        signature = sign(body, timestamp=int(time.time()) - 600)
        assert post_event(body, signature=signature).status_code == 400

    def test_rejects_a_garbled_header(self, post_event):
        assert post_event(event(), signature="not-a-stripe-header").status_code == 400


class TestPayload:
    @pytest.mark.parametrize("body", ["{not json", '["an", "array"]'])
    def test_rejects_a_signed_body_that_isnt_an_event(self, post_event, body):
        response = post_event(body)
        assert response.status_code == 400
        assert response.json() == {"detail": "Malformed payload."}

    @pytest.mark.parametrize(
        "event_type",
        ["checkout.session.completed", "checkout.session.expired", "charge.refunded"],
    )
    def test_acknowledges_a_valid_event(self, post_event, event_type):
        response = post_event(event(event_type))
        assert response.status_code == 200
        assert response.json() == {"status": "ignored", "type": event_type}
