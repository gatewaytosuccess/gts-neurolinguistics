from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from commerce.models import Order, OrderItem, OrderStatus
from users.authentication import ClerkAuthentication
from users.models import Role, User

from .helpers import make_course

pytestmark = pytest.mark.django_db


@pytest.fixture
def signed_in(monkeypatch):
    """Stubs only token verification; the status check runs for real."""
    monkeypatch.setattr(
        ClerkAuthentication, "decode_token", lambda self, token: {"sub": "user_admin"}
    )


@pytest.fixture
def admin(signed_in):
    return User.objects.create_user(
        email="admin@example.com", clerk_user_id="user_admin", role=Role.ADMIN
    )


def make_buyer(email="ada@example.com", **fields):
    return User.objects.create_user(email=email, **fields)


def make_order(user, courses=(), status=OrderStatus.PAID, days_ago=None):
    total = sum(course.price_cents for course in courses)
    order = Order.objects.create(user=user, status=status, subtotal_cents=total, total_cents=total)
    for course in courses:
        OrderItem.objects.create(order=order, course=course, unit_price_cents=course.price_cents)
    if days_ago is not None:
        Order.objects.filter(pk=order.pk).update(
            created_at=timezone.now() - timedelta(days=days_ago)
        )
    return order


def get_orders(client, params=None):
    return client.get(
        reverse("admin-order-list"), params or {}, headers={"Authorization": "Bearer stub"}
    )


def list_orders(client, params=None):
    response = get_orders(client, params)
    assert response.status_code == 200, response.json()
    return response.json()


def ids(body):
    return [item["id"] for item in body["results"]]


class TestAccess:
    def test_rejects_a_request_with_no_token(self, client):
        assert client.get(reverse("admin-order-list")).status_code == 401

    @pytest.mark.parametrize("role", [Role.LEARNER, Role.INSTRUCTOR])
    def test_forbids_every_other_role(self, client, signed_in, role):
        User.objects.create_user(email="admin@example.com", clerk_user_id="user_admin", role=role)
        assert get_orders(client).status_code == 403


class TestListing:
    def test_lists_every_status_newest_first(self, client, admin):
        ada = make_buyer()
        expired = make_order(ada, status=OrderStatus.EXPIRED, days_ago=3)
        refunded = make_order(ada, status=OrderStatus.REFUNDED, days_ago=2)
        paid = make_order(ada, status=OrderStatus.PAID, days_ago=1)
        pending = make_order(ada, status=OrderStatus.PENDING, days_ago=0)

        assert ids(list_orders(client)) == [
            str(pending.pk),
            str(paid.pk),
            str(refunded.pk),
            str(expired.pk),
        ]

    def test_includes_every_buyer(self, client, admin):
        make_order(make_buyer("ada@example.com"))
        make_order(make_buyer("grace@example.com"))

        assert list_orders(client)["count"] == 2


class TestStatusFilter:
    @pytest.fixture
    def orders(self):
        ada = make_buyer()
        return {status: make_order(ada, status=status) for status in OrderStatus.values}

    @pytest.mark.parametrize("status", OrderStatus.values)
    def test_filters_to_one_status(self, client, admin, orders, status):
        assert ids(list_orders(client, {"status": status})) == [str(orders[status].pk)]

    def test_blank_means_no_filter(self, client, admin, orders):
        assert list_orders(client, {"status": ""})["count"] == 4

    @pytest.mark.parametrize("status", ["cancelled", "PAID"])
    def test_an_unknown_status_is_a_400(self, client, admin, status):
        response = get_orders(client, {"status": status})

        assert response.status_code == 400
        assert "status" in response.json()


class TestSearch:
    @pytest.fixture
    def orders(self):
        return {
            "ada": make_order(make_buyer("ada.l@example.com", name="Ada Lovelace")),
            "grace": make_order(make_buyer("grace@example.com", name="Grace Hopper")),
        }

    def test_matches_part_of_the_buyers_name_case_insensitively(self, client, admin, orders):
        assert ids(list_orders(client, {"q": "LOVE"})) == [str(orders["ada"].pk)]

    def test_matches_part_of_the_buyers_email_case_insensitively(self, client, admin, orders):
        assert ids(list_orders(client, {"q": "Ada.L@"})) == [str(orders["ada"].pk)]

    def test_matches_the_exact_order_id(self, client, admin, orders):
        assert ids(list_orders(client, {"q": str(orders["grace"].pk)})) == [str(orders["grace"].pk)]

    def test_does_not_match_part_of_an_order_id(self, client, admin, orders):
        assert list_orders(client, {"q": str(orders["grace"].pk)[:8]})["count"] == 0

    def test_blank_means_no_filter(self, client, admin, orders):
        assert list_orders(client, {"q": "  "})["count"] == 2

    def test_combines_with_the_status_filter(self, client, admin):
        ada = make_buyer(name="Ada")
        paid = make_order(ada, status=OrderStatus.PAID)
        make_order(ada, status=OrderStatus.EXPIRED)
        make_order(make_buyer("grace@example.com", name="Grace"), status=OrderStatus.PAID)

        assert ids(list_orders(client, {"q": "ada", "status": OrderStatus.PAID})) == [str(paid.pk)]


class TestPagination:
    def test_is_paginated_at_20(self, client, admin):
        ada = make_buyer()
        for _ in range(21):
            make_order(ada)

        first = list_orders(client)
        second = list_orders(client, {"page": 2})

        assert first["count"] == 21
        assert len(first["results"]) == 20
        assert len(second["results"]) == 1

    def test_filters_survive_pagination(self, client, admin):
        ada = make_buyer()
        for _ in range(21):
            make_order(ada, status=OrderStatus.EXPIRED)
            make_order(ada, status=OrderStatus.PAID)

        first = list_orders(client, {"q": "ada", "status": OrderStatus.EXPIRED})

        assert first["count"] == 21
        assert "status=expired" in first["next"]
        assert "q=ada" in first["next"]

    def test_a_page_past_the_last_is_a_404(self, client, admin):
        assert get_orders(client, {"page": 2}).status_code == 404


class TestPayload:
    def test_returns_the_row_fields(self, client, admin):
        ada = make_buyer(name="Ada Lovelace")
        syntax = make_course("syntax", price_cents=4900)
        foundations = make_course("foundations", price_cents=12900)
        order = make_order(ada, [syntax, foundations], status=OrderStatus.REFUNDED)

        (item,) = list_orders(client)["results"]

        assert item == {
            "id": str(order.pk),
            "created_at": item["created_at"],
            "status": "refunded",
            "total_cents": 17800,
            "buyer": {"id": str(ada.pk), "name": "Ada Lovelace", "email": "ada@example.com"},
            "items": [{"title": "Foundations"}, {"title": "Syntax"}],
        }

    def test_does_not_query_per_order(self, client, admin, django_assert_num_queries):
        course = make_course()
        for i in range(3):
            make_order(make_buyer(f"learner-{i}@example.com"), [course])

        # The admin lookup, the paginator's count, one page of orders with
        # their buyers, and their items with courses.
        with django_assert_num_queries(4):
            list_orders(client)
