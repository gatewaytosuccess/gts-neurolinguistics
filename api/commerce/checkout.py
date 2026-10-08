"""Starting a checkout and fulfilling the order it pays for.

Order code takes a list of courses so a cart can sit in front of it later; the
web app sends one course per checkout.
"""

import logging
import time
from urllib.parse import quote

import stripe
from django.conf import settings
from django.db import transaction

from enrollments.models import Enrollment, EnrollmentSource, EnrollmentStatus
from users.models import User

from . import stripe_api
from .models import Order, OrderItem, OrderStatus

logger = logging.getLogger(__name__)

CURRENCY = "usd"
SESSION_LIFETIME_SECONDS = 60 * 60


class AlreadyEnrolled(Exception):
    """The user holds an active enrollment in one of the courses."""


def start_checkout(user, courses):
    """Creates a ``pending`` order for ``courses`` and its Checkout Session.

    Returns the order, whose ``payment_ref`` is the session id, and the session's
    URL. Raises ``AlreadyEnrolled`` before anything is written, and
    ``stripe.StripeError`` with nothing written if Stripe refuses. ``courses``
    must be non-empty and are not checked for being published.
    """
    with transaction.atomic():
        # Serialises one user's checkouts, so two can't each create a Customer.
        user = User.objects.select_for_update().get(pk=user.pk)
        if Enrollment.objects.filter(
            user=user, course__in=courses, status=EnrollmentStatus.ACTIVE
        ).exists():
            raise AlreadyEnrolled

        customer_id = ensure_customer(user)
        total = sum(course.price_cents for course in courses)
        order = Order.objects.create(
            user=user, status=OrderStatus.PENDING, subtotal_cents=total, total_cents=total
        )
        items = [
            OrderItem.objects.create(
                order=order, course=course, unit_price_cents=course.price_cents
            )
            for course in courses
        ]
        session = stripe_api.create_checkout_session(
            session_params(order, items, customer_id, landing=courses[0].slug)
        )
        order.payment_ref = session.id
        order.save(update_fields=["payment_ref", "updated_at"])

    logger.info("User %s started checkout %s for order %s.", user.pk, session.id, order.pk)
    return order, session.url


def ensure_customer(user):
    """The user's Stripe Customer id, creating the Customer on first checkout.

    An existing Customer's email is overwritten with the user's, so it never
    stays stale after an email change. Expects ``user`` locked.
    """
    if user.stripe_customer_id:
        stripe_api.update_customer_email(user.stripe_customer_id, user.email)
        return user.stripe_customer_id

    user.stripe_customer_id = stripe_api.create_customer(
        email=user.email, name=user.name, user_id=user.pk
    )
    user.save(update_fields=["stripe_customer_id", "updated_at"])
    return user.stripe_customer_id


def session_params(order, items, customer_id, *, landing):
    slug = quote(landing)
    return {
        "mode": "payment",
        "customer": customer_id,
        "client_reference_id": str(order.user_id),
        "line_items": [
            {
                "quantity": 1,
                "price_data": {
                    "currency": CURRENCY,
                    "unit_amount": item.unit_price_cents,
                    "product_data": {"name": item.course.title},
                },
            }
            for item in items
        ],
        "metadata": {"order_id": str(order.pk)},
        "expires_at": int(time.time()) + SESSION_LIFETIME_SECONDS,
        # Stripe substitutes {CHECKOUT_SESSION_ID} on redirect.
        "success_url": f"{settings.WEB_APP_URL}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{settings.WEB_APP_URL}/courses/{slug}",
    }


def fulfil(order, session):
    """Marks a ``pending`` order paid and enrolls its user in its courses.

    ``session`` is the order's Checkout Session as a plain dict: a webhook
    event's object, or ``to_dict()`` of a retrieved one. Does nothing unless the
    order is pending and the session is this order's and paid, so it is safe to
    call any number of times. An amount or currency that doesn't match the order
    is logged and enrolls nobody. An enrollment that is already active is left
    as it is.
    """
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)
        if order.status != OrderStatus.PENDING:
            return order
        if session.get("id") != order.payment_ref:
            logger.error(
                "Session %s is not order %s's session %s; not fulfilling.",
                session.get("id"),
                order.pk,
                order.payment_ref,
            )
            return order
        if session.get("payment_status") != "paid":
            return order
        if session.get("amount_total") != order.total_cents or session.get("currency") != CURRENCY:
            logger.error(
                "Session %s charged %s %s but order %s totals %s %s; not fulfilling.",
                session.get("id"),
                session.get("amount_total"),
                session.get("currency"),
                order.pk,
                order.total_cents,
                CURRENCY,
            )
            return order

        order.status = OrderStatus.PAID
        order.receipt_url = receipt_url(session)
        order.save(update_fields=["status", "receipt_url", "updated_at"])
        for item in order.items.all():
            enroll(order, item.course_id)

    logger.info("Fulfilled order %s for user %s.", order.pk, order.user_id)
    return order


def confirm(order):
    """Fulfils a ``pending`` order if Stripe now reports its session paid.

    Returns the order as it stands. Any other status returns without calling
    Stripe, and a pending order stays pending when Stripe can't be reached.
    """
    if order.status != OrderStatus.PENDING:
        return order
    try:
        session = stripe_api.retrieve_checkout_session(order.payment_ref).to_dict()
    except stripe.StripeError:
        logger.exception("Could not fetch session %s for order %s.", order.payment_ref, order.pk)
        return order
    return fulfil(order, session)


def receipt_url(session):
    """Blank when Stripe can't be reached: a missing receipt link doesn't hold up access."""
    payment_intent = session.get("payment_intent")
    if not payment_intent:
        return ""
    try:
        charge = stripe_api.retrieve_payment_intent(payment_intent).latest_charge
    except stripe.StripeError:
        logger.exception("Could not fetch the receipt for session %s.", session.get("id"))
        return ""
    return (charge.receipt_url if charge else "") or ""


def enroll(order, course_id):
    """Expects to run inside ``fulfil``'s transaction."""
    enrollment = (
        Enrollment.objects.select_for_update()
        .filter(user_id=order.user_id, course_id=course_id)
        .first()
    )
    if enrollment is None:
        Enrollment.objects.create(
            user_id=order.user_id,
            course_id=course_id,
            source=EnrollmentSource.PURCHASE,
            order=order,
        )
        return
    if enrollment.status == EnrollmentStatus.REVOKED:
        # enrolled_at and progress are kept: buying again picks up where they left off.
        enrollment.status = EnrollmentStatus.ACTIVE
        enrollment.revoked_at = None
        enrollment.source = EnrollmentSource.PURCHASE
        enrollment.order = order
        enrollment.save(update_fields=["status", "revoked_at", "source", "order"])
        return
    logger.warning(
        "Order %s paid for course %s, which user %s already holds through enrollment %s (%s).",
        order.pk,
        course_id,
        order.user_id,
        enrollment.pk,
        enrollment.source,
    )
