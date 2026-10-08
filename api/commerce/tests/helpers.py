from commerce.models import Order, OrderItem, OrderStatus
from courses.models import Course, CourseStatus
from users.models import User


def make_user(email="learner@example.com", **fields):
    fields.setdefault("clerk_user_id", "user_learner")
    return User.objects.create_user(email=email, **fields)


def make_course(slug="neuro-101", status=CourseStatus.PUBLISHED, price_cents=12900):
    return Course.objects.create(
        slug=slug, title=slug.title(), price_cents=price_cents, status=status
    )


def pending_order(user, course, *, session_id="cs_test_pending"):
    order = Order.objects.create(
        user=user,
        status=OrderStatus.PENDING,
        subtotal_cents=course.price_cents,
        total_cents=course.price_cents,
        payment_ref=session_id,
    )
    OrderItem.objects.create(order=order, course=course, unit_price_cents=course.price_cents)
    return order


def paid_session(order, **fields):
    """The ``checkout.session.completed`` object Stripe sends for ``order``."""
    return {
        "id": order.payment_ref,
        "object": "checkout.session",
        "payment_status": "paid",
        "amount_total": order.total_cents,
        "currency": "usd",
        "payment_intent": "pi_test",
        "metadata": {"order_id": str(order.pk)},
        **fields,
    }
