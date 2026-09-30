import uuid
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from commerce.models import Order, OrderItem, OrderStatus
from courses.models import Course, CourseStatus
from reviews.models import Review, ReviewStatus
from users.authentication import ClerkAuthentication
from users.models import Role, User, UserStatus

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


@pytest.fixture
def learner():
    return User.objects.create_user(
        email="learner@example.com",
        clerk_user_id="user_learner",
        name="Ada Learner",
        avatar_url="https://img.example.com/ada.png",
    )


def course(slug, status=CourseStatus.PUBLISHED):
    return Course.objects.create(
        slug=slug, title=slug.replace("-", " ").title(), price_cents=12900, status=status
    )


def days_ago(days):
    return timezone.now() - timedelta(days=days)


def order(user, courses, created_days_ago, status=OrderStatus.PAID):
    total = sum(c.price_cents for c in courses)
    placed = Order.objects.create(user=user, status=status, subtotal_cents=total, total_cents=total)
    for c in courses:
        OrderItem.objects.create(order=placed, course=c, unit_price_cents=c.price_cents)
    Order.objects.filter(pk=placed.pk).update(created_at=days_ago(created_days_ago))
    return placed


def review(user, reviewed, created_days_ago, status=ReviewStatus.PUBLISHED, rating=5):
    written = Review.objects.create(
        user=user, course=reviewed, rating=rating, body="Clear and useful.", status=status
    )
    Review.objects.filter(pk=written.pk).update(created_at=days_ago(created_days_ago))
    return written


def get_user(client, pk):
    return client.get(
        reverse("admin-user-detail", args=[pk]), headers={"Authorization": "Bearer stub"}
    )


def fetch_user(client, pk):
    response = get_user(client, pk)
    assert response.status_code == 200, response.json()
    return response.json()


class TestAccess:
    def test_rejects_a_request_with_no_token(self, client, learner):
        assert client.get(reverse("admin-user-detail", args=[learner.pk])).status_code == 401

    @pytest.mark.parametrize("role", [Role.LEARNER, Role.INSTRUCTOR])
    def test_forbids_every_other_role(self, client, signed_in, learner, role):
        User.objects.create_user(email="admin@example.com", clerk_user_id="user_admin", role=role)
        assert get_user(client, learner.pk).status_code == 403

    def test_an_unknown_id_is_a_404(self, client, admin):
        assert get_user(client, uuid.uuid4()).status_code == 404

    @pytest.mark.parametrize("malformed", ["not-a-uuid", "12345"])
    def test_a_malformed_id_is_a_404(self, client, admin, malformed):
        response = client.get(
            f"/api/admin/users/{malformed}/", headers={"Authorization": "Bearer stub"}
        )
        assert response.status_code == 404


class TestProfile:
    def test_payload_shape(self, client, admin, learner):
        body = fetch_user(client, learner.pk)

        assert set(body) == {
            "id",
            "email",
            "name",
            "avatar_url",
            "role",
            "status",
            "suspended_at",
            "suspension_reason",
            "created_at",
            "has_clerk_identity",
            "orders",
            "reviews",
        }
        assert body["id"] == str(learner.pk)
        assert body["email"] == "learner@example.com"
        assert body["name"] == "Ada Learner"
        assert body["avatar_url"] == "https://img.example.com/ada.png"
        assert body["role"] == Role.LEARNER
        assert body["status"] == UserStatus.ACTIVE
        assert body["suspended_at"] is None
        assert body["suspension_reason"] == ""
        assert body["has_clerk_identity"] is True
        assert body["orders"] == []
        assert body["reviews"] == []

    def test_never_exposes_the_clerk_id(self, client, admin, learner):
        assert "user_learner" not in get_user(client, learner.pk).content.decode()

    def test_a_suspended_user_has_its_date_and_reason(self, client, admin, learner):
        learner.suspend("Chargeback fraud")

        body = fetch_user(client, learner.pk)

        assert body["status"] == UserStatus.SUSPENDED
        assert body["suspended_at"] is not None
        assert body["suspension_reason"] == "Chargeback fraud"

    def test_a_deleted_user_has_no_clerk_identity_and_keeps_its_history(self, client, admin):
        deleted = User.objects.create_user(email="gone@example.com", status=UserStatus.DELETED)
        bought = course("intro")
        order(deleted, [bought], created_days_ago=3)
        review(deleted, bought, created_days_ago=2)

        body = fetch_user(client, deleted.pk)

        assert body["status"] == UserStatus.DELETED
        assert body["has_clerk_identity"] is False
        assert len(body["orders"]) == 1
        assert len(body["reviews"]) == 1


class TestOrders:
    def test_newest_first_with_their_items(self, client, admin, learner):
        intro = course("intro")
        advanced = course("advanced")
        older = order(learner, [intro], created_days_ago=10)
        newer = order(learner, [intro, advanced], created_days_ago=1, status=OrderStatus.REFUNDED)

        orders = fetch_user(client, learner.pk)["orders"]

        assert [o["id"] for o in orders] == [str(newer.pk), str(older.pk)]
        assert orders[0]["status"] == OrderStatus.REFUNDED
        assert orders[0]["total_cents"] == 25800
        assert orders[0]["created_at"]
        assert sorted(orders[0]["items"], key=lambda item: item["title"]) == [
            {"title": "Advanced", "unit_price_cents": 12900},
            {"title": "Intro", "unit_price_cents": 12900},
        ]

    def test_only_this_users_orders(self, client, admin, learner):
        order(admin, [course("intro")], created_days_ago=1)

        assert fetch_user(client, learner.pk)["orders"] == []


class TestReviews:
    def test_newest_first_hidden_ones_and_draft_courses_included(self, client, admin, learner):
        published = course("intro")
        draft = course("advanced", status=CourseStatus.DRAFT)
        hidden = review(learner, published, created_days_ago=5, status=ReviewStatus.HIDDEN)
        on_draft = review(learner, draft, created_days_ago=1, rating=3)

        reviews = fetch_user(client, learner.pk)["reviews"]

        assert [r["id"] for r in reviews] == [str(on_draft.pk), str(hidden.pk)]
        assert reviews[0]["rating"] == 3
        assert reviews[0]["body"] == "Clear and useful."
        assert reviews[0]["status"] == ReviewStatus.PUBLISHED
        assert reviews[0]["created_at"]
        assert reviews[0]["course"] == {
            "id": str(draft.pk),
            "title": "Advanced",
            "slug": "advanced",
            "status": CourseStatus.DRAFT,
        }
        assert reviews[1]["status"] == ReviewStatus.HIDDEN
        assert reviews[1]["course"]["status"] == CourseStatus.PUBLISHED

    def test_only_this_users_reviews(self, client, admin, learner):
        review(admin, course("intro"), created_days_ago=1)

        assert fetch_user(client, learner.pk)["reviews"] == []
