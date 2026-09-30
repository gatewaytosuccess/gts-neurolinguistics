from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from courses.models import Course, CourseStatus
from reviews.models import Review, ReviewStatus
from reviews.serializers import author_name
from users.models import User, UserStatus

pytestmark = pytest.mark.django_db


def make_course(slug="foundations", status=CourseStatus.PUBLISHED):
    return Course.objects.create(slug=slug, title=slug.title(), price_cents=12900, status=status)


def make_review(course, name="Maria Garcia", body="Clear and useful.", **fields):
    index = Review.objects.count()
    user = fields.pop("user", None) or User.objects.create_user(
        email=f"reviewer{index}@example.com", name=name
    )
    fields.setdefault("rating", 4)
    return Review.objects.create(user=user, course=course, body=body, **fields)


def backdate(review, days):
    Review.objects.filter(pk=review.pk).update(created_at=timezone.now() - timedelta(days=days))


def get_reviews(client, slug="foundations", **params):
    return client.get(reverse("course-review-list", kwargs={"slug": slug}), params)


def listed_ids(response):
    return [review["id"] for review in response.json()["results"]]


class TestVisibility:
    def test_a_draft_is_not_found(self, client):
        make_course("draft-course", status=CourseStatus.DRAFT)

        assert get_reviews(client, "draft-course").status_code == 404

    def test_an_unknown_slug_is_not_found(self, client):
        make_course()

        assert get_reviews(client, "no-such-course").status_code == 404

    def test_a_course_with_no_reviews_is_an_empty_page(self, client):
        make_course()

        response = get_reviews(client)

        assert response.status_code == 200
        assert response.json()["count"] == 0
        assert response.json()["results"] == []

    def test_ignores_an_invalid_token(self, client):
        course = make_course()
        make_review(course)

        response = client.get(
            reverse("course-review-list", kwargs={"slug": "foundations"}),
            headers={"Authorization": "Bearer not-a-token"},
        )

        assert response.status_code == 200


class TestFiltering:
    def test_hidden_reviews_are_not_listed(self, client):
        course = make_course()
        shown = make_review(course)
        make_review(course, status=ReviewStatus.HIDDEN)

        assert listed_ids(get_reviews(client)) == [str(shown.id)]

    @pytest.mark.parametrize("body", ["", "   \n\t "])
    def test_rating_only_reviews_are_not_listed(self, client, body):
        course = make_course()
        shown = make_review(course)
        make_review(course, body=body)

        assert listed_ids(get_reviews(client)) == [str(shown.id)]

    def test_only_this_courses_reviews(self, client):
        course = make_course()
        shown = make_review(course)
        make_review(make_course("other-course"))

        assert listed_ids(get_reviews(client)) == [str(shown.id)]

    @pytest.mark.parametrize(
        "status", [UserStatus.SUSPENDED, UserStatus.BANNED, UserStatus.DELETED]
    )
    def test_the_authors_account_status_does_not_matter(self, client, status):
        course = make_course()
        author = User.objects.create_user(
            email="author@example.com", name="Ana Ruiz", status=status
        )
        review = make_review(course, user=author)

        assert listed_ids(get_reviews(client)) == [str(review.id)]


class TestOrderingAndPagination:
    def test_newest_first(self, client):
        course = make_course()
        oldest, newest, middle = make_review(course), make_review(course), make_review(course)
        backdate(oldest, 3)
        backdate(middle, 2)
        backdate(newest, 1)

        assert listed_ids(get_reviews(client)) == [str(newest.id), str(middle.id), str(oldest.id)]

    def test_ten_per_page(self, client):
        course = make_course()
        reviews = [make_review(course) for _ in range(11)]
        for age, review in enumerate(reviews):
            backdate(review, age)

        first = get_reviews(client).json()
        second = get_reviews(client, page=2).json()

        assert first["count"] == 11
        assert [r["id"] for r in first["results"]] == [str(r.id) for r in reviews[:10]]
        assert first["next"] is not None
        assert [r["id"] for r in second["results"]] == [str(reviews[10].id)]
        assert second["next"] is None

    def test_a_page_past_the_last_is_not_found(self, client):
        make_review(make_course())

        assert get_reviews(client, page=2).status_code == 404


class TestPayload:
    def test_fields(self, client):
        course = make_course()
        review = make_review(course, name="Maria Garcia", body="Line one.\nLine two.", rating=5)

        (payload,) = get_reviews(client).json()["results"]

        assert set(payload) == {"id", "rating", "body", "author_name", "created_at", "updated_at"}
        assert payload["id"] == str(review.id)
        assert payload["rating"] == 5
        assert payload["body"] == "Line one.\nLine two."
        assert payload["author_name"] == "Maria G."

    def test_never_exposes_the_authors_email(self, client):
        make_review(make_course())

        assert "reviewer0@example.com" not in get_reviews(client).content.decode()


class TestAuthorName:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("Maria Garcia", "Maria G."),
            ("maria garcia", "maria G."),
            ("Maria José Garcia López", "Maria L."),
            ("  Maria   Garcia  ", "Maria G."),
            ("Cher", "Cher"),
            ("  Cher ", "Cher"),
            ("", ""),
        ],
    )
    def test_first_name_and_last_initial(self, name, expected):
        assert author_name(name) == expected
