import json
import time

import pytest
import stripe
from django.urls import reverse

from commerce.models import Order, OrderStatus
from enrollments.models import Enrollment, EnrollmentSource

from .helpers import expired_session, make_course, make_user, paid_session, pending_order

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


def event(event_type="checkout.session.completed", obj=None):
    return json.dumps(
        {"id": "evt_test", "object": "event", "type": event_type, "data": {"object": obj or {}}}
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

    @pytest.mark.parametrize("event_type", ["charge.refunded", "charge.dispute.created"])
    def test_acknowledges_an_event_it_doesnt_handle(self, post_event, event_type):
        response = post_event(event(event_type))
        assert response.status_code == 200
        assert response.json() == {"status": "ignored", "type": event_type}


@pytest.mark.django_db
class TestSessionCompleted:
    def test_fulfils_the_order(self, post_event, fake_stripe):
        learner, course = make_user(), make_course()
        order = pending_order(learner, course)

        response = post_event(event(obj=paid_session(order)))

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "order_status": "paid"}
        order.refresh_from_db()
        assert order.status == OrderStatus.PAID
        assert Enrollment.objects.filter(user=learner, course=course, order=order).exists()

    def test_a_redelivery_changes_nothing(self, post_event, fake_stripe):
        order = pending_order(make_user(), make_course())
        body = event(obj=paid_session(order))
        post_event(body)

        response = post_event(body)

        assert response.json() == {"status": "ok", "order_status": "paid"}
        assert Enrollment.objects.count() == 1

    @pytest.mark.parametrize(
        "metadata",
        [{}, {"order_id": "not-a-uuid"}, {"order_id": "00000000-0000-0000-0000-000000000000"}],
        ids=["missing", "malformed", "unknown"],
    )
    def test_acknowledges_a_session_with_no_known_order(self, post_event, metadata):
        response = post_event(event(obj={"id": "cs_test_x", "metadata": metadata}))

        assert response.status_code == 200
        assert response.json() == {"status": "unknown"}

    def test_asks_for_a_retry_when_a_duplicates_refund_fails(self, post_event, fake_stripe):
        learner, course = make_user(), make_course()
        earlier = Order.objects.create(
            user=learner, status=OrderStatus.PAID, subtotal_cents=100, total_cents=100
        )
        Enrollment.objects.create(
            user=learner, course=course, source=EnrollmentSource.PURCHASE, order=earlier
        )
        order = pending_order(learner, course)
        fake_stripe.fail = stripe.APIConnectionError("Stripe is unreachable")

        response = post_event(event(obj=paid_session(order)))

        assert response.status_code == 503
        order.refresh_from_db()
        assert order.status == OrderStatus.PENDING


@pytest.mark.django_db
class TestSessionExpired:
    def test_expires_a_pending_order(self, post_event):
        order = pending_order(make_user(), make_course())

        response = post_event(event("checkout.session.expired", expired_session(order)))

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "order_status": "expired"}
        order.refresh_from_db()
        assert order.status == OrderStatus.EXPIRED

    @pytest.mark.parametrize("status", [OrderStatus.PAID, OrderStatus.REFUNDED])
    def test_a_settled_order_is_left_alone(self, post_event, status):
        order = pending_order(make_user(), make_course())
        order.status = status
        order.save()

        response = post_event(event("checkout.session.expired", expired_session(order)))

        assert response.json() == {"status": "ok", "order_status": status}
        order.refresh_from_db()
        assert order.status == status

    def test_another_orders_session_is_ignored(self, post_event):
        order = pending_order(make_user(), make_course())

        post_event(event("checkout.session.expired", expired_session(order, id="cs_test_other")))

        order.refresh_from_db()
        assert order.status == OrderStatus.PENDING

    def test_acknowledges_a_session_with_no_known_order(self, post_event):
        response = post_event(
            event("checkout.session.expired", {"id": "cs_test_x", "metadata": {}})
        )

        assert response.status_code == 200
        assert response.json() == {"status": "unknown"}
