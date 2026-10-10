import logging
import threading
from datetime import timedelta

import pytest
import stripe
from django.db import connection
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

    def test_saves_the_payment_intent(self, fake_stripe, order):
        fulfil(order, paid_session(order))

        order.refresh_from_db()
        assert order.payment_intent_id == "pi_test"

    def test_records_no_refund(self, fake_stripe, order):
        fulfil(order, paid_session(order))

        order.refresh_from_db()
        assert (order.refunded_cents, order.refunded_at) == (0, None)

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

    @pytest.mark.parametrize("source", [EnrollmentSource.MANUAL, EnrollmentSource.COMP])
    def test_an_active_grant_is_taken_over(self, fake_stripe, learner, course, order, source):
        grant = Enrollment.objects.create(user=learner, course=course, source=source)

        fulfil(order, paid_session(order))

        order.refresh_from_db()
        assert order.status == OrderStatus.PAID
        enrollment = Enrollment.objects.get(user=learner, course=course)
        assert enrollment.pk == grant.pk
        assert enrollment.enrolled_at == grant.enrolled_at
        assert (enrollment.source, enrollment.order) == (EnrollmentSource.PURCHASE, order)
        assert fake_stripe.named("create_refund") == []

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


class TestAnEarlierPurchase:
    @pytest.fixture
    def bought(self, learner, course):
        earlier = Order.objects.create(
            user=learner,
            status=OrderStatus.PAID,
            subtotal_cents=course.price_cents,
            total_cents=course.price_cents,
        )
        return Enrollment.objects.create(
            user=learner, course=course, source=EnrollmentSource.PURCHASE, order=earlier
        )

    def test_refunds_the_order_in_full(self, fake_stripe, bought, order):
        fulfil(order, paid_session(order))

        order.refresh_from_db()
        assert order.status == OrderStatus.REFUNDED
        assert fake_stripe.named("create_refund") == [
            ("create_refund", ("pi_test",), {"idempotency_key": f"refund-{order.pk}"})
        ]

    def test_records_the_refund_with_no_admin(self, fake_stripe, bought, order):
        fulfil(order, paid_session(order))

        order.refresh_from_db()
        assert order.payment_intent_id == "pi_test"
        assert order.refunded_cents == order.total_cents
        assert order.refunded_at is not None
        assert (order.refunded_by, order.refund_reason) == (None, "")

    def test_leaves_the_existing_enrollment_as_it_is(self, fake_stripe, bought, order):
        before = list(Enrollment.objects.values())

        fulfil(order, paid_session(order))

        assert list(Enrollment.objects.values()) == before

    def test_refunds_once_when_run_twice(self, fake_stripe, bought, order):
        session = paid_session(order)

        fulfil(order, session)
        fulfil(order, session)

        assert len(fake_stripe.named("create_refund")) == 1

    def test_a_refund_stripe_refuses_leaves_the_order_pending(self, fake_stripe, bought, order):
        fake_stripe.fail = stripe.APIConnectionError("Stripe is unreachable")

        with pytest.raises(stripe.APIConnectionError):
            fulfil(order, paid_session(order))

        order.refresh_from_db()
        assert order.status == OrderStatus.PENDING
        assert (order.payment_intent_id, order.refunded_cents) == ("", 0)


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


@pytest.mark.django_db(transaction=True)
def test_two_orders_paid_at_once_enroll_once_and_refund_the_other(fake_stripe):
    learner, course = make_user(), make_course()
    orders = [pending_order(learner, course, session_id=f"cs_test_{n}") for n in range(2)]
    start = threading.Barrier(2)

    def arrive(order):
        try:
            start.wait()
            fulfil(order, paid_session(order))
        finally:
            connection.close()

    threads = [threading.Thread(target=arrive, args=(order,)) for order in orders]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    statuses = sorted(Order.objects.values_list("status", flat=True))
    assert statuses == [OrderStatus.PAID, OrderStatus.REFUNDED]
    paid = Order.objects.get(status=OrderStatus.PAID)
    assert Enrollment.objects.get(user=learner, course=course).order == paid
    assert len(fake_stripe.named("create_refund")) == 1
