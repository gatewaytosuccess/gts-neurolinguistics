import logging
from datetime import timedelta

import pytest
import stripe
from django.utils import timezone

from commerce.checkout import fulfil
from commerce.models import Order, OrderStatus
from courses.models import CourseStatus, Lesson, Module
from enrollments.models import (
    Enrollment,
    EnrollmentSource,
    EnrollmentStatus,
    LessonProgress,
    ProgressStatus,
)

from .helpers import make_course, make_user, paid_session, pending_order

pytestmark = pytest.mark.django_db


@pytest.fixture
def learner():
    return make_user()


@pytest.fixture
def course():
    return make_course()


@pytest.fixture
def order(learner, course):
    return pending_order(learner, course)


def revoked(user, course, **fields):
    enrollment = Enrollment.objects.create(
        user=user, course=course, status=EnrollmentStatus.REVOKED, **fields
    )
    # auto_now_add ignores a value passed to create().
    long_ago = timezone.now() - timedelta(days=90)
    Enrollment.objects.filter(pk=enrollment.pk).update(
        enrolled_at=long_ago, revoked_at=long_ago + timedelta(days=30)
    )
    enrollment.refresh_from_db()
    return enrollment


class TestFulfilling:
    def test_marks_the_order_paid_with_its_receipt(self, fake_stripe, order):
        fulfil(order, paid_session(order))

        order.refresh_from_db()
        assert order.status == OrderStatus.PAID
        assert order.receipt_url == "https://pay.stripe.com/receipts/test"
        assert fake_stripe.named("retrieve_payment_intent") == [
            ("retrieve_payment_intent", ("pi_test",), {})
        ]

    def test_creates_an_enrollment(self, fake_stripe, learner, course, order):
        fulfil(order, paid_session(order))

        enrollment = Enrollment.objects.get(user=learner, course=course)
        assert enrollment.status == EnrollmentStatus.ACTIVE
        assert enrollment.source == EnrollmentSource.PURCHASE
        assert enrollment.order == order

    def test_reactivates_a_revoked_purchase_with_the_new_order(
        self, fake_stripe, learner, course, order
    ):
        earlier = Order.objects.create(
            user=learner, status=OrderStatus.PAID, subtotal_cents=9900, total_cents=9900
        )
        enrollment = revoked(learner, course, source=EnrollmentSource.PURCHASE, order=earlier)
        lesson = Lesson.objects.create(
            module=Module.objects.create(course=course, title="Module", position=1),
            title="Lesson",
            position=1,
        )
        LessonProgress.objects.create(user=learner, lesson=lesson, status=ProgressStatus.COMPLETED)

        fulfil(order, paid_session(order))

        reactivated = Enrollment.objects.get(user=learner, course=course)
        assert reactivated.pk == enrollment.pk
        assert reactivated.status == EnrollmentStatus.ACTIVE
        assert reactivated.revoked_at is None
        assert reactivated.order == order
        assert reactivated.enrolled_at == enrollment.enrolled_at
        assert LessonProgress.objects.get(user=learner).status == ProgressStatus.COMPLETED

    @pytest.mark.parametrize("source", [EnrollmentSource.MANUAL, EnrollmentSource.COMP])
    def test_a_revoked_grant_becomes_a_purchase(self, fake_stripe, learner, course, order, source):
        revoked(learner, course, source=source)

        fulfil(order, paid_session(order))

        enrollment = Enrollment.objects.get(user=learner, course=course)
        assert enrollment.status == EnrollmentStatus.ACTIVE
        assert enrollment.source == EnrollmentSource.PURCHASE
        assert enrollment.order == order

    def test_a_course_unpublished_since_checkout_is_still_fulfilled(
        self, fake_stripe, learner, course, order
    ):
        course.status = CourseStatus.DRAFT
        course.save()

        fulfil(order, paid_session(order))

        assert Enrollment.objects.filter(user=learner, course=course).exists()

    def test_a_receipt_stripe_cant_give_leaves_the_link_blank(self, fake_stripe, learner, order):
        fake_stripe.fail = stripe.APIConnectionError("Stripe is unreachable")

        fulfil(order, paid_session(order))

        order.refresh_from_db()
        assert order.status == OrderStatus.PAID
        assert order.receipt_url == ""
        assert Enrollment.objects.filter(user=learner).exists()


class TestIdempotence:
    def test_running_twice_changes_nothing(self, fake_stripe, learner, order):
        session = paid_session(order)
        fulfil(order, session)
        first_order = Order.objects.values().get(pk=order.pk)
        first_enrollments = list(Enrollment.objects.values())

        fulfil(order, session)

        assert Order.objects.values().get(pk=order.pk) == first_order
        assert list(Enrollment.objects.values()) == first_enrollments
        assert len(fake_stripe.named("retrieve_payment_intent")) == 1

    def test_an_active_enrollment_is_left_alone(self, fake_stripe, learner, course, order, caplog):
        Enrollment.objects.create(user=learner, course=course, source=EnrollmentSource.COMP)
        before = list(Enrollment.objects.values())

        with caplog.at_level(logging.WARNING, logger="commerce.checkout"):
            fulfil(order, paid_session(order))

        assert list(Enrollment.objects.values()) == before
        assert "already holds" in caplog.text


class TestRefusals:
    @pytest.mark.parametrize(
        "fields",
        [{"amount_total": 100}, {"currency": "eur"}],
        ids=["amount", "currency"],
    )
    def test_a_mismatch_enrolls_nobody(self, fake_stripe, order, fields, caplog):
        with caplog.at_level(logging.ERROR, logger="commerce.checkout"):
            fulfil(order, paid_session(order, **fields))

        order.refresh_from_db()
        assert order.status == OrderStatus.PENDING
        assert not Enrollment.objects.exists()
        assert "not fulfilling" in caplog.text

    def test_an_unpaid_session_does_nothing(self, fake_stripe, order):
        fulfil(order, paid_session(order, payment_status="unpaid"))

        order.refresh_from_db()
        assert order.status == OrderStatus.PENDING
        assert not Enrollment.objects.exists()

    def test_another_orders_session_does_nothing(self, fake_stripe, order):
        fulfil(order, paid_session(order, id="cs_test_someone_else"))

        order.refresh_from_db()
        assert order.status == OrderStatus.PENDING
        assert not Enrollment.objects.exists()

    @pytest.mark.parametrize("status", [OrderStatus.EXPIRED, OrderStatus.REFUNDED])
    def test_an_order_that_isnt_pending_is_left_alone(self, fake_stripe, order, status):
        order.status = status
        order.save()

        fulfil(order, paid_session(order))

        order.refresh_from_db()
        assert order.status == status
        assert not Enrollment.objects.exists()
