import pytest
from django.urls import reverse

from courses.models import Course, CourseStatus
from reviews.models import Review, ReviewStatus
from users.models import User

pytestmark = pytest.mark.django_db


def make_course(slug, status=CourseStatus.PUBLISHED, **fields):
    fields.setdefault("title", slug.replace("-", " ").title())
    fields.setdefault("price_cents", 12900)
    return Course.objects.create(slug=slug, status=status, **fields)


def get_course(client, slug, **headers):
    return client.get(reverse("course-detail", kwargs={"slug": slug}), headers=headers)


class TestVisibility:
    def test_returns_a_published_course(self, client):
        make_course("foundations")

        response = get_course(client, "foundations")

        assert response.status_code == 200
        assert response.json()["slug"] == "foundations"

    def test_a_draft_is_not_found(self, client):
        make_course("draft-course", status=CourseStatus.DRAFT)

        assert get_course(client, "draft-course").status_code == 404

    def test_an_unknown_slug_is_not_found(self, client):
        make_course("foundations")

        assert get_course(client, "no-such-course").status_code == 404


class TestPayload:
    def test_matches_the_list_item(self, client):
        course = make_course(
            "foundations",
            title="Foundations",
            description="Where language sits.",
            price_cents=14900,
            thumbnail_key="thumbnails/abc/thumb.png",
        )
        reviewer = User.objects.create_user(email="reviewer@example.com")
        Review.objects.create(user=reviewer, course=course, rating=4, status=ReviewStatus.PUBLISHED)

        (list_item,) = client.get(reverse("course-list")).json()["results"]

        assert get_course(client, "foundations").json() == list_item


class TestAccess:
    def test_ignores_an_invalid_token(self, client):
        make_course("foundations")

        response = get_course(client, "foundations", Authorization="Bearer not-a-real-token")

        assert response.status_code == 200
