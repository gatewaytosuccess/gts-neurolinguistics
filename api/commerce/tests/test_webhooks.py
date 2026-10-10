import json
import time

import pytest
import stripe
from django.urls import reverse

from commerce.models import Order, OrderStatus
from enrollments.models import Enrollment, EnrollmentSource, EnrollmentStatus

from .helpers import (
    expired_session,
    make_course,
    make_user,
    paid_session,
    pending_order,
    refunded_charge,
)

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

    @pytest.mark.parametrize("event_type", ["customer.created", "charge.succeeded"])
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


def settled_order(status=OrderStatus.PAID):
    """An order in ``status`` whose charge is ``pi_test``, with its enrollment."""
    learner, course = make_user(), make_course()
    order = pending_order(learner, course)
    order.status = status
    order.save()
    Enrollment.objects.create(
        user=learner, course=course, source=EnrollmentSource.PURCHASE, order=order
    )
    return order


@pytest.mark.django_db
class TestChargeRefunded:
    @pytest.fixture
    def order(self, fake_stripe):
        order = settled_order()
        fake_stripe.payment_intents["pi_test"] = {"order_id": str(order.pk)}
        return order

    def test_a_full_refund_marks_the_order_refunded(self, post_event, order):
        response = post_event(event("charge.refunded", refunded_charge()))

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "order_status": "refunded"}
        order.refresh_from_db()
        assert order.status == OrderStatus.REFUNDED

    def test_a_full_refund_records_the_amount_and_time_but_no_admin(self, post_event, order):
        post_event(event("charge.refunded", refunded_charge()))

        order.refresh_from_db()
        assert order.refunded_cents == order.total_cents
        assert order.refunded_at is not None
        assert (order.refunded_by, order.refund_reason) == (None, "")

    def test_a_full_refund_leaves_the_enrollment_active(self, post_event, order):
        post_event(event("charge.refunded", refunded_charge()))

        enrollment = Enrollment.objects.get(order=order)
        assert enrollment.status == EnrollmentStatus.ACTIVE

    def test_a_partial_refund_leaves_the_order_paid(self, post_event, order):
        response = post_event(event("charge.refunded", refunded_charge(amount_refunded=5000)))

        assert response.json() == {"status": "ok", "order_status": "paid"}
        order.refresh_from_db()
        assert order.status == OrderStatus.PAID
        assert (order.refunded_cents, order.refunded_at) == (5000, None)

    def test_a_second_partial_refund_adds_to_the_first(self, post_event, order):
        post_event(event("charge.refunded", refunded_charge(amount_refunded=500)))
        post_event(event("charge.refunded", refunded_charge(amount_refunded=1500)))

        order.refresh_from_db()
        assert (order.status, order.refunded_cents) == (OrderStatus.PAID, 1500)

    def test_partial_refunds_that_add_up_mark_the_order_refunded(self, post_event, order):
        post_event(event("charge.refunded", refunded_charge(amount_refunded=500)))
        post_event(event("charge.refunded", refunded_charge()))

        order.refresh_from_db()
        assert order.status == OrderStatus.REFUNDED
        assert order.refunded_cents == order.total_cents
        assert order.refunded_at is not None

    def test_an_event_arriving_late_never_lowers_the_amount(self, post_event, order):
        post_event(event("charge.refunded", refunded_charge(amount_refunded=1500)))
        post_event(event("charge.refunded", refunded_charge(amount_refunded=500)))

        order.refresh_from_db()
        assert order.refunded_cents == 1500

    def test_a_redelivery_changes_nothing(self, post_event, order):
        body = event("charge.refunded", refunded_charge())
        post_event(body)
        first = Order.objects.values().get(pk=order.pk)

        response = post_event(body)

        assert response.json() == {"status": "ok", "order_status": "refunded"}
        assert Order.objects.values().get(pk=order.pk) == first

    def test_a_duplicate_payments_automatic_refund_is_already_settled(
        self, post_event, fake_stripe
    ):
        order = settled_order(OrderStatus.REFUNDED)
        fake_stripe.payment_intents["pi_test"] = {"order_id": str(order.pk)}

        response = post_event(event("charge.refunded", refunded_charge()))

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "order_status": "refunded"}

    def test_a_pending_order_stays_pending_with_the_refund_recorded(self, post_event, fake_stripe):
        order = pending_order(make_user(), make_course())
        fake_stripe.payment_intents["pi_test"] = {"order_id": str(order.pk)}

        post_event(event("charge.refunded", refunded_charge(amount_refunded=500)))

        order.refresh_from_db()
        assert (order.status, order.refunded_cents) == (OrderStatus.PENDING, 500)

    def test_a_charge_without_amount_refunded_changes_nothing(self, post_event, order):
        before = Order.objects.values().get(pk=order.pk)

        response = post_event(event("charge.refunded", refunded_charge(amount_refunded=None)))

        assert response.status_code == 200
        assert Order.objects.values().get(pk=order.pk) == before

    def test_finds_the_order_through_the_payment_intent(self, post_event, fake_stripe, order):
        post_event(event("charge.refunded", refunded_charge()))

        assert fake_stripe.named("retrieve_payment_intent_metadata") == [
            ("retrieve_payment_intent_metadata", ("pi_test",), {})
        ]

    @pytest.mark.parametrize(
        "charge, metadata",
        [
            (refunded_charge(payment_intent=None), {}),
            (refunded_charge(payment_intent="pi_unknown"), {}),
            (refunded_charge(), {}),
            (refunded_charge(), {"order_id": "not-a-uuid"}),
            (refunded_charge(), {"order_id": "00000000-0000-0000-0000-000000000000"}),
        ],
        ids=["no-payment-intent", "unknown-payment-intent", "missing", "malformed", "unknown"],
    )
    def test_acknowledges_a_charge_with_no_known_order(
        self, post_event, fake_stripe, charge, metadata
    ):
        fake_stripe.payment_intents["pi_test"] = metadata

        response = post_event(event("charge.refunded", charge))

        assert response.status_code == 200
        assert response.json() == {"status": "unknown"}

    def test_asks_for_a_retry_when_stripe_is_unreachable(self, post_event, fake_stripe, order):
        fake_stripe.fail = stripe.APIConnectionError("Stripe is unreachable")

        response = post_event(event("charge.refunded", refunded_charge()))

        assert response.status_code == 503
        order.refresh_from_db()
        assert order.status == OrderStatus.PAID


@pytest.mark.django_db
class TestDisputeCreated:
    def dispute(self):
        return {
            "id": "dp_test",
            "object": "dispute",
            "amount": 12900,
            "currency": "usd",
            "charge": "ch_test",
            "payment_intent": "pi_test",
            "reason": "fraudulent",
        }

    def test_logs_the_dispute_with_its_order(self, post_event, fake_stripe, caplog):
        order = settled_order()
        fake_stripe.payment_intents["pi_test"] = {"order_id": str(order.pk)}

        response = post_event(event("charge.dispute.created", self.dispute()))

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert f"dp_test opened on charge ch_test (order {order.pk})" in caplog.text
        order.refresh_from_db()
        assert order.status == OrderStatus.PAID

    def test_acknowledges_a_dispute_whose_order_cant_be_found(
        self, post_event, fake_stripe, caplog
    ):
        fake_stripe.fail = stripe.APIConnectionError("Stripe is unreachable")

        response = post_event(event("charge.dispute.created", self.dispute()))

        assert response.status_code == 200
        assert "(order unknown)" in caplog.text
