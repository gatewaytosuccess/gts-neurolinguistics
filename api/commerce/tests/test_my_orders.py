import pytest
from django.urls import reverse

from commerce.models import Order, OrderItem, OrderStatus
from users.authentication import ClerkAuthentication

from .helpers import make_course, make_user, pending_order

pytestmark = pytest.mark.django_db

AUTH = {"Authorization": "Bearer stub"}


@pytest.fixture
def learner(monkeypatch):
    """Stubs only token verification; the status check runs for real."""
    monkeypatch.setattr(
        ClerkAuthentication, "decode_token", lambda self, token: {"sub": "user_learner"}
    )
    return make_user()


def settled_order(user, course, status=OrderStatus.PAID, **fields):
    order = pending_order(user, course, session_id=f"cs_test_{course.slug}")
    for name, value in {"status": status, **fields}.items():
        setattr(order, name, value)
    order.save()
    return order


def list_orders(client):
    return client.get(reverse("user-me-orders"), headers=AUTH)


def get_order(client, order):
    return client.get(reverse("user-me-order", kwargs={"pk": order.pk}), headers=AUTH)


class TestOrderList:
    def test_lists_paid_and_refunded_orders_newest_first(self, client, learner):
        older = settled_order(learner, make_course(slug="neuro-101"))
        newer = settled_order(learner, make_course(slug="neuro-201"), OrderStatus.REFUNDED)

        response = list_orders(client)

        assert response.status_code == 200
        assert [(row["id"], row["status"]) for row in response.json()] == [
            (str(newer.pk), "refunded"),
            (str(older.pk), "paid"),
        ]

    def test_each_order_carries_its_courses_and_total(self, client, learner):
        order = settled_order(learner, make_course(slug="neuro-101", price_cents=12900))

        [row] = list_orders(client).json()

        assert row["total_cents"] == 12900
        assert row["created_at"] == order.created_at.isoformat().replace("+00:00", "Z")
        assert row["items"] == [
            {"course_slug": "neuro-101", "course_title": "Neuro-101", "unit_price_cents": 12900}
        ]

    @pytest.mark.parametrize("status", [OrderStatus.PENDING, OrderStatus.EXPIRED])
    def test_leaves_out_orders_nothing_was_bought_with(self, client, learner, status):
        settled_order(learner, make_course(), status)

        assert list_orders(client).json() == []

    def test_leaves_out_other_users_orders(self, client, learner):
        settled_order(make_user("other@example.com", clerk_user_id="user_other"), make_course())

        assert list_orders(client).json() == []

    def test_requires_signing_in(self, client):
        assert client.get(reverse("user-me-orders")).status_code in (401, 403)


class TestOrderDetail:
    def test_answers_the_order_as_recorded(self, client, learner):
        course = make_course(slug="neuro-101", price_cents=12900)
        order = settled_order(
            learner,
            course,
            subtotal_cents=12900,
            discount_cents=2900,
            total_cents=10000,
            receipt_url="https://pay.stripe.com/receipts/test",
        )
        course.price_cents = 19900
        course.save()

        response = get_order(client, order)

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == str(order.pk)
        assert body["status"] == "paid"
        assert (body["subtotal_cents"], body["discount_cents"], body["total_cents"]) == (
            12900,
            2900,
            10000,
        )
        assert body["receipt_url"] == "https://pay.stripe.com/receipts/test"
        assert body["items"] == [
            {"course_slug": "neuro-101", "course_title": "Neuro-101", "unit_price_cents": 12900}
        ]

    def test_answers_a_refunded_order(self, client, learner):
        order = settled_order(learner, make_course(), OrderStatus.REFUNDED)

        assert get_order(client, order).json()["status"] == "refunded"

    @pytest.mark.parametrize("status", [OrderStatus.PENDING, OrderStatus.EXPIRED])
    def test_an_unbought_order_is_not_found(self, client, learner, status):
        order = settled_order(learner, make_course(), status)

        assert get_order(client, order).status_code == 404

    def test_another_users_order_is_not_found(self, client, learner):
        other = make_user("other@example.com", clerk_user_id="user_other")
        order = settled_order(other, make_course())

        assert get_order(client, order).status_code == 404

    def test_an_unknown_order_is_not_found(self, client, learner):
        order = Order(pk="00000000-0000-0000-0000-000000000000")

        assert get_order(client, order).status_code == 404


def test_an_order_lists_every_course_it_bought(client, learner):
    order = settled_order(learner, make_course(slug="neuro-101"))
    OrderItem.objects.create(
        order=order, course=make_course(slug="neuro-201"), unit_price_cents=500
    )

    [row] = list_orders(client).json()

    assert sorted(item["course_slug"] for item in row["items"]) == ["neuro-101", "neuro-201"]
