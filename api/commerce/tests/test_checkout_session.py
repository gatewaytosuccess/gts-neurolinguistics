import json
import threading

import pytest
import stripe
from django.db import connection
from django.test import Client
from django.urls import reverse

from commerce.models import Order, OrderStatus
from enrollments.models import Enrollment, EnrollmentSource
from users.authentication import ClerkAuthentication

from .helpers import make_course, make_user, paid_session, pending_order

AUTH = {"Authorization": "Bearer stub"}
WEBHOOK_SECRET = "whsec_a-test-signing-secret"


@pytest.fixture
def learner(monkeypatch):
    """Stubs only token verification; the status check runs for real."""
    monkeypatch.setattr(
        ClerkAuthentication, "decode_token", lambda self, token: {"sub": "user_learner"}
    )
    return make_user()


@pytest.fixture
def course():
    return make_course(slug="neuro-101", price_cents=12900)


@pytest.fixture
def order(learner, course):
    return pending_order(learner, course, session_id="cs_test_mine")


def confirm(client, session_id):
    return client.get(reverse("checkout-session", kwargs={"session_id": session_id}), headers=AUTH)


def send_webhook(client, session):
    body = json.dumps(
        {
            "id": "evt_test",
            "object": "event",
            "type": "checkout.session.completed",
            "data": {"object": session},
        }
    )
    signature = stripe.WebhookSignature.generate_signature_header(body, WEBHOOK_SECRET)
    return client.post(
        reverse("stripe-webhook"),
        data=body,
        content_type="application/json",
        headers={"Stripe-Signature": signature},
    )


@pytest.mark.django_db
class TestConfirming:
    def test_a_paid_session_fulfils_the_order(self, client, fake_stripe, learner, course, order):
        fake_stripe.sessions[order.payment_ref] = paid_session(order)

        response = confirm(client, order.payment_ref)

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == str(order.pk)
        assert body["status"] == OrderStatus.PAID
        assert body["total_cents"] == 12900
        assert body["items"] == [
            {"course_slug": "neuro-101", "course_title": "Neuro-101", "unit_price_cents": 12900}
        ]
        enrollment = Enrollment.objects.get(user=learner, course=course)
        assert (enrollment.source, enrollment.order) == (EnrollmentSource.PURCHASE, order)

    def test_an_unpaid_session_leaves_the_order_pending(self, client, fake_stripe, order):
        fake_stripe.sessions[order.payment_ref] = paid_session(order, payment_status="unpaid")

        response = confirm(client, order.payment_ref)

        assert response.status_code == 200
        assert response.json()["status"] == OrderStatus.PENDING
        assert not Enrollment.objects.exists()

    def test_the_order_stays_pending_when_stripe_is_unreachable(self, client, fake_stripe, order):
        fake_stripe.sessions[order.payment_ref] = paid_session(order)
        fake_stripe.fail = stripe.APIConnectionError("Stripe is unreachable")

        response = confirm(client, order.payment_ref)

        assert response.status_code == 200
        assert response.json()["status"] == OrderStatus.PENDING
        assert not Enrollment.objects.exists()

    def test_the_order_stays_pending_when_a_duplicates_refund_fails(
        self, client, fake_stripe, learner, course, order
    ):
        earlier = Order.objects.create(
            user=learner, status=OrderStatus.PAID, subtotal_cents=100, total_cents=100
        )
        Enrollment.objects.create(
            user=learner, course=course, source=EnrollmentSource.PURCHASE, order=earlier
        )
        fake_stripe.sessions[order.payment_ref] = paid_session(order)
        fake_stripe.refuse_refunds = True

        response = confirm(client, order.payment_ref)

        assert response.status_code == 200
        assert response.json()["status"] == OrderStatus.PENDING

    def test_a_settled_order_is_answered_without_asking_stripe(self, client, fake_stripe, order):
        order.status = OrderStatus.PAID
        order.save()

        response = confirm(client, order.payment_ref)

        assert response.json()["status"] == OrderStatus.PAID
        assert fake_stripe.calls == []


@pytest.mark.django_db
class TestRefusals:
    def test_404_for_another_users_session(self, client, fake_stripe, learner, course):
        someone_else = make_user(email="other@example.com", clerk_user_id="user_other")
        theirs = pending_order(someone_else, course, session_id="cs_test_theirs")
        fake_stripe.sessions[theirs.payment_ref] = paid_session(theirs)

        response = confirm(client, theirs.payment_ref)

        assert response.status_code == 404
        assert fake_stripe.calls == []
        theirs.refresh_from_db()
        assert theirs.status == OrderStatus.PENDING
        assert not Enrollment.objects.exists()

    def test_404_for_an_unknown_session(self, client, fake_stripe, learner):
        assert confirm(client, "cs_test_nobodys").status_code == 404
        assert fake_stripe.calls == []

    def test_401_signed_out(self, client, fake_stripe, order):
        response = client.get(reverse("checkout-session", kwargs={"session_id": order.payment_ref}))
        assert response.status_code == 401


@pytest.mark.django_db
class TestWithTheWebhook:
    @pytest.fixture(autouse=True)
    def signing_secret(self, settings):
        settings.STRIPE_WEBHOOK_SECRET = WEBHOOK_SECRET

    @pytest.mark.parametrize("webhook_first", [True, False], ids=["webhook", "success-page"])
    def test_either_arriving_first_leaves_one_paid_order_and_one_enrollment(
        self, client, fake_stripe, learner, order, webhook_first
    ):
        session = paid_session(order)
        fake_stripe.sessions[order.payment_ref] = session
        arrivals = [lambda: send_webhook(client, session), lambda: confirm(client, session["id"])]

        for arrive in arrivals if webhook_first else reversed(arrivals):
            assert arrive().status_code == 200

        order.refresh_from_db()
        assert order.status == OrderStatus.PAID
        assert Enrollment.objects.filter(user=learner).count() == 1
        assert len(fake_stripe.named("retrieve_payment_intent")) == 1


@pytest.mark.django_db(transaction=True)
def test_racing_the_webhook_leaves_one_paid_order_and_one_enrollment(
    settings, fake_stripe, learner, order
):
    settings.STRIPE_WEBHOOK_SECRET = WEBHOOK_SECRET
    session = paid_session(order)
    fake_stripe.sessions[order.payment_ref] = session
    start = threading.Barrier(2)
    statuses = []

    def arrive(request):
        try:
            start.wait()
            statuses.append(request(Client()).status_code)
        finally:
            connection.close()

    threads = [
        threading.Thread(target=arrive, args=(lambda c: send_webhook(c, session),)),
        threading.Thread(target=arrive, args=(lambda c: confirm(c, session["id"]),)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert statuses == [200, 200]
    order.refresh_from_db()
    assert order.status == OrderStatus.PAID
    assert Enrollment.objects.filter(user=learner).count() == 1
    assert len(fake_stripe.named("retrieve_payment_intent")) == 1
