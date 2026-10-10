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
from django.utils import timezone

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
    URL. The user's other open checkouts for any of ``courses`` are expired.
    Raises ``AlreadyEnrolled`` before anything is written, and
    ``stripe.StripeError`` with nothing written if Stripe refuses the new
    session. ``courses`` must be non-empty and are not checked for being
    published.
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
        expire_open_checkouts(user, courses, keep=order)

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


def expire_open_checkouts(user, courses, *, keep):
    """Expires the sessions of ``user``'s pending orders for any of ``courses``,
    other than ``keep``, and marks those orders ``expired``.

    A session Stripe won't expire is logged and its order left pending: it may
    have just been paid, and if not, ``checkout.session.expired`` settles it.
    Expects ``user`` locked.
    """
    open_orders = (
        Order.objects.select_for_update()
        .filter(
            user=user,
            status=OrderStatus.PENDING,
            pk__in=OrderItem.objects.filter(course__in=courses).values("order_id"),
        )
        .exclude(pk=keep.pk)
    )
    for order in open_orders:
        try:
            stripe_api.expire_checkout_session(order.payment_ref)
        except stripe.StripeError:
            logger.warning(
                "Could not expire session %s for order %s.",
                order.payment_ref,
                order.pk,
                exc_info=True,
            )
            continue
        order.status = OrderStatus.EXPIRED
        order.save(update_fields=["status", "updated_at"])
        logger.info("Expired order %s, replaced by order %s.", order.pk, keep.pk)


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
        # Charge events carry only the PaymentIntent, so it names the order too.
        "payment_intent_data": {"metadata": {"order_id": str(order.pk)}},
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
    is logged and enrolls nobody.

    If the user already holds one of the courses through an earlier purchase,
    the whole order is refunded through Stripe, marked ``refunded``, and nobody
    is enrolled. Raises ``stripe.StripeError`` with nothing written if that
    refund fails.
    """
    with transaction.atomic():
        # Serialises one user's fulfilments, so two orders for a course can't both enroll.
        User.objects.select_for_update().get(pk=order.user_id)
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

        order.payment_intent_id = session.get("payment_intent") or ""
        order.receipt_url = receipt_url(session)
        if already_bought(order):
            refund(order, session)
            order.status = OrderStatus.REFUNDED
            order.refunded_cents = order.total_cents
            order.refunded_at = timezone.now()
        else:
            order.status = OrderStatus.PAID
            for item in order.items.all():
                enroll(order, item.course_id)
        order.save(
            update_fields=[
                "status",
                "payment_intent_id",
                "receipt_url",
                "refunded_cents",
                "refunded_at",
                "updated_at",
            ]
        )

    logger.info("Fulfilled order %s for user %s: %s.", order.pk, order.user_id, order.status)
    return order


def expire(order, session):
    """Marks a ``pending`` order ``expired`` when ``session``, a
    ``checkout.session.expired`` object, is its session. Any other order is
    left as it is, so one already paid stays paid.
    """
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)
        if order.status != OrderStatus.PENDING or session.get("id") != order.payment_ref:
            return order
        order.status = OrderStatus.EXPIRED
        order.save(update_fields=["status", "updated_at"])

    logger.info("Order %s expired unpaid.", order.pk)
    return order


def record_refund(order, charge):
    """Records how much of ``charge``, a ``charge.refunded`` object, has gone
    back, whatever the order's status. Once all of it has, sets ``refunded_at``
    if unset and marks a ``paid`` order ``refunded``. Saves nothing when there
    is nothing new. Enrollments are never touched.
    """
    amount_refunded = charge.get("amount_refunded")
    if not isinstance(amount_refunded, int):
        logger.error("Refunded charge %s has no amount_refunded; ignoring it.", charge.get("id"))
        return order
    in_full = amount_refunded == charge.get("amount")

    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)
        changed = []
        # amount_refunded only grows, and events can arrive out of order.
        if amount_refunded > order.refunded_cents:
            order.refunded_cents = amount_refunded
            changed.append("refunded_cents")
        if in_full and order.refunded_at is None:
            order.refunded_at = timezone.now()
            changed.append("refunded_at")
        if in_full and order.status == OrderStatus.PAID:
            order.status = OrderStatus.REFUNDED
            changed.append("status")
        if not changed:
            return order
        order.save(update_fields=[*changed, "updated_at"])

    logger.info(
        "Order %s has %s of %s cents refunded (%s).",
        order.pk,
        order.refunded_cents,
        order.total_cents,
        order.status,
    )
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
        return fulfil(order, session)
    except stripe.StripeError:
        logger.exception("Could not confirm session %s for order %s.", order.payment_ref, order.pk)
        return order


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


def already_bought(order):
    """Whether the user holds one of ``order``'s courses through an earlier purchase."""
    return Enrollment.objects.filter(
        user_id=order.user_id,
        course__order_items__order=order,
        status=EnrollmentStatus.ACTIVE,
        source=EnrollmentSource.PURCHASE,
    ).exists()


def refund(order, session):
    logger.warning(
        "Order %s paid for a course user %s already bought; refunding it.",
        order.pk,
        order.user_id,
    )
    # The key makes a retry after a rolled-back fulfil return the first refund.
    stripe_api.create_refund(session.get("payment_intent"), idempotency_key=f"refund-{order.pk}")


def enroll(order, course_id):
    """Expects to run inside ``fulfil``'s transaction, for a course the user
    doesn't hold through a purchase."""
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
    # A revoked enrollment or an active grant becomes this order's purchase.
    # enrolled_at and progress are kept: buying again picks up where they left off.
    enrollment.status = EnrollmentStatus.ACTIVE
    enrollment.revoked_at = None
    enrollment.source = EnrollmentSource.PURCHASE
    enrollment.order = order
    enrollment.save(update_fields=["status", "revoked_at", "source", "order"])
