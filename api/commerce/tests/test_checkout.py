import time

import pytest
import stripe
from django.urls import reverse

from commerce.models import Order, OrderItem, OrderStatus
from courses.models import CourseStatus
from enrollments.models import Enrollment, EnrollmentSource, EnrollmentStatus
from users.authentication import ClerkAuthentication

from .helpers import make_course, make_user

pytestmark = pytest.mark.django_db

AUTH = {"Authorization": "Bearer stub"}


@pytest.fixture(autouse=True)
def web_app_url(settings):
    settings.WEB_APP_URL = "https://gts.example.com"


@pytest.fixture
def learner(monkeypatch):
    """Stubs only token verification; the status check runs for real."""
    monkeypatch.setattr(
        ClerkAuthentication, "decode_token", lambda self, token: {"sub": "user_learner"}
    )
    return make_user(name="Ada Lovelace")


def checkout(client, slug):
    return client.post(
        reverse("checkout"), {"course": slug}, content_type="application/json", headers=AUTH
    )


class TestStartingACheckout:
    def test_creates_a_pending_order_at_the_courses_price(self, client, fake_stripe, learner):
        course = make_course(price_cents=12900)

        response = checkout(client, course.slug)

        assert response.status_code == 201
        order = Order.objects.get(user=learner)
        assert order.status == OrderStatus.PENDING
        assert (order.subtotal_cents, order.discount_cents, order.total_cents) == (12900, 0, 12900)
        item = OrderItem.objects.get(order=order)
        assert (item.course, item.unit_price_cents) == (course, 12900)

    def test_answers_the_sessions_url_and_stores_its_id(self, client, fake_stripe, learner):
        response = checkout(client, make_course().slug)

        order = Order.objects.get(user=learner)
        assert order.payment_ref.startswith("cs_test_")
        assert response.json() == {"url": f"https://checkout.stripe.com/c/pay/{order.payment_ref}"}

    def test_the_session_charges_the_snapshot_price(self, client, fake_stripe, learner):
        course = make_course(slug="neuro-101", price_cents=12900)

        checkout(client, course.slug)

        order = Order.objects.get(user=learner)
        learner.refresh_from_db()
        [(_, (params,), _)] = fake_stripe.named("create_checkout_session")
        assert params["mode"] == "payment"
        assert params["customer"] == learner.stripe_customer_id
        assert params["client_reference_id"] == str(learner.pk)
        assert params["metadata"] == {"order_id": str(order.pk)}
        assert params["line_items"] == [
            {
                "quantity": 1,
                "price_data": {
                    "currency": "usd",
                    "unit_amount": 12900,
                    "product_data": {"name": "Neuro-101"},
                },
            }
        ]
        assert params["success_url"] == (
            "https://gts.example.com/checkout/success?session_id={CHECKOUT_SESSION_ID}"
        )
        assert params["cancel_url"] == "https://gts.example.com/courses/neuro-101"

    def test_the_session_expires_in_an_hour(self, client, fake_stripe, learner):
        checkout(client, make_course().slug)

        [(_, (params,), _)] = fake_stripe.named("create_checkout_session")
        assert abs(params["expires_at"] - (time.time() + 3600)) < 60

    def test_a_revoked_learner_can_buy_again(self, client, fake_stripe, learner):
        course = make_course()
        Enrollment.objects.create(
            user=learner,
            course=course,
            source=EnrollmentSource.MANUAL,
            status=EnrollmentStatus.REVOKED,
        )

        assert checkout(client, course.slug).status_code == 201


class TestRefusals:
    def test_409_while_enrolled(self, client, fake_stripe, learner):
        course = make_course()
        Enrollment.objects.create(user=learner, course=course, source=EnrollmentSource.COMP)

        response = checkout(client, course.slug)

        assert response.status_code == 409
        assert response.json()["code"] == "already_enrolled"
        assert not Order.objects.exists()
        assert fake_stripe.calls == []

    def test_404_for_a_draft(self, client, fake_stripe, learner):
        course = make_course(status=CourseStatus.DRAFT)

        assert checkout(client, course.slug).status_code == 404
        assert not Order.objects.exists()

    def test_404_for_an_unknown_course(self, client, fake_stripe, learner):
        assert checkout(client, "no-such-course").status_code == 404

    def test_400_without_a_course(self, client, fake_stripe, learner):
        response = client.post(
            reverse("checkout"), {}, content_type="application/json", headers=AUTH
        )
        assert response.status_code == 400

    def test_401_signed_out(self, client, fake_stripe):
        response = client.post(
            reverse("checkout"), {"course": make_course().slug}, content_type="application/json"
        )
        assert response.status_code == 401

    def test_502_and_nothing_kept_when_stripe_refuses(self, client, fake_stripe, learner):
        course = make_course()
        fake_stripe.fail = stripe.APIConnectionError("Stripe is unreachable")

        response = checkout(client, course.slug)

        assert response.status_code == 502
        assert not Order.objects.exists()
        learner.refresh_from_db()
        assert learner.stripe_customer_id is None


class TestStripeCustomer:
    def test_is_created_at_the_first_checkout(self, client, fake_stripe, learner):
        checkout(client, make_course().slug)

        [(_, _, fields)] = fake_stripe.named("create_customer")
        assert fields == {"email": learner.email, "name": "Ada Lovelace", "user_id": learner.pk}
        learner.refresh_from_db()
        assert learner.stripe_customer_id.startswith("cus_")

    def test_is_reused_by_later_checkouts(self, client, fake_stripe, learner):
        checkout(client, make_course(slug="first").slug)
        learner.refresh_from_db()
        customer_id = learner.stripe_customer_id

        checkout(client, make_course(slug="second").slug)

        assert len(fake_stripe.named("create_customer")) == 1
        sessions = fake_stripe.named("create_checkout_session")
        assert [params["customer"] for _, (params,), _ in sessions] == [customer_id, customer_id]
        learner.refresh_from_db()
        assert learner.stripe_customer_id == customer_id

    def test_gets_the_users_current_email(self, client, fake_stripe, learner):
        learner.stripe_customer_id = "cus_existing"
        learner.email = "ada@new.example.com"
        learner.save()

        checkout(client, make_course().slug)

        assert fake_stripe.named("update_customer_email") == [
            ("update_customer_email", ("cus_existing", "ada@new.example.com"), {})
        ]
        assert fake_stripe.named("create_customer") == []
