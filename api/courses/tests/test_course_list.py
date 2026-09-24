from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from courses.models import Course, CourseStatus
from reviews.models import Review, ReviewStatus
from users.authentication import ClerkAuthentication
from users.models import User, UserStatus

pytestmark = pytest.mark.django_db


def make_course(slug, status=CourseStatus.PUBLISHED, **fields):
    fields.setdefault("title", slug.replace("-", " ").title())
    fields.setdefault("price_cents", 12900)
    return Course.objects.create(slug=slug, status=status, **fields)


def review(course, rating, status=ReviewStatus.PUBLISHED):
    user = User.objects.create_user(email=f"reviewer-{Review.objects.count()}@example.com")
    return Review.objects.create(user=user, course=course, rating=rating, status=status)


def list_courses(client, params=None, **headers):
    response = client.get(reverse("course-list"), params or {}, headers=headers)
    assert response.status_code == 200
    return response.json()


def by_slug(body):
    return {item["slug"]: item for item in body["results"]}


def slugs(body):
    return [item["slug"] for item in body["results"]]


def age(course, days):
    Course.objects.filter(pk=course.pk).update(created_at=timezone.now() - timedelta(days=days))


class TestVisibility:
    def test_excludes_drafts(self, client):
        make_course("published-course")
        make_course("draft-course", status=CourseStatus.DRAFT)

        assert list(by_slug(list_courses(client))) == ["published-course"]

    def test_lists_newest_first(self, client):
        now = timezone.now()
        for days_ago, slug in [(2, "oldest"), (0, "newest"), (1, "middle")]:
            course = make_course(slug)
            Course.objects.filter(pk=course.pk).update(created_at=now - timedelta(days=days_ago))

        slugs = [item["slug"] for item in list_courses(client)["results"]]

        assert slugs == ["newest", "middle", "oldest"]

    def test_is_paginated_at_the_default_page_size(self, client, settings):
        for i in range(settings.REST_FRAMEWORK["PAGE_SIZE"] + 1):
            make_course(f"course-{i}")

        body = list_courses(client)

        assert body["count"] == settings.REST_FRAMEWORK["PAGE_SIZE"] + 1
        assert len(body["results"]) == settings.REST_FRAMEWORK["PAGE_SIZE"]
        assert body["next"] is not None


class TestSearch:
    def test_matches_a_word_in_the_title_case_insensitively(self, client):
        make_course("aphasia", title="Understanding Aphasia")
        make_course("syntax", title="Syntax in the Brain")

        assert slugs(list_courses(client, {"q": "APHASIA"})) == ["aphasia"]

    def test_matches_a_word_in_the_description_case_insensitively(self, client):
        make_course("foundations", description="Where BROCA'S area sits.")
        make_course("syntax", description="Trees and movement.")

        assert slugs(list_courses(client, {"q": "broca"})) == ["foundations"]

    def test_never_matches_drafts(self, client):
        make_course("published-aphasia", title="Aphasia")
        make_course("draft-aphasia", title="Aphasia", status=CourseStatus.DRAFT)

        assert slugs(list_courses(client, {"q": "aphasia"})) == ["published-aphasia"]

    def test_blank_means_no_filter(self, client):
        make_course("aphasia")
        make_course("syntax")

        assert len(list_courses(client, {"q": "  "})["results"]) == 2

    def test_no_match_returns_an_empty_page(self, client):
        make_course("aphasia")

        body = list_courses(client, {"q": "quantum"})

        assert body["count"] == 0
        assert body["results"] == []


class TestSort:
    def make_priced(self):
        """Two courses share each price, so every price sort has a tie to break."""
        for slug, price, days_ago in [
            ("cheap-old", 9900, 3),
            ("cheap-new", 9900, 1),
            ("dear-old", 19900, 2),
            ("dear-new", 19900, 0),
        ]:
            age(make_course(slug, price_cents=price), days_ago)

    def test_price_asc_breaks_ties_by_newest(self, client):
        self.make_priced()

        assert slugs(list_courses(client, {"sort": "price_asc"})) == [
            "cheap-new",
            "cheap-old",
            "dear-new",
            "dear-old",
        ]

    def test_price_desc_breaks_ties_by_newest(self, client):
        self.make_priced()

        assert slugs(list_courses(client, {"sort": "price_desc"})) == [
            "dear-new",
            "dear-old",
            "cheap-new",
            "cheap-old",
        ]

    def test_newest(self, client):
        self.make_priced()

        assert slugs(list_courses(client, {"sort": "newest"})) == [
            "dear-new",
            "cheap-new",
            "dear-old",
            "cheap-old",
        ]

    def test_an_unknown_sort_behaves_like_newest(self, client):
        self.make_priced()

        assert slugs(list_courses(client, {"sort": "popularity"})) == slugs(
            list_courses(client, {"sort": "newest"})
        )

    def test_combines_with_search(self, client):
        age(make_course("aphasia-cheap", title="Aphasia I", price_cents=9900), 0)
        age(make_course("aphasia-dear", title="Aphasia II", price_cents=19900), 1)
        make_course("syntax", price_cents=100)

        body = list_courses(client, {"q": "aphasia", "sort": "price_desc"})

        assert slugs(body) == ["aphasia-dear", "aphasia-cheap"]


class TestPayload:
    def test_returns_the_catalog_fields(self, client, settings):
        settings.CLOUDFRONT_DOMAIN = "cdn.example.com"
        make_course(
            "foundations",
            title="Foundations",
            description="Where language sits.",
            price_cents=14900,
            thumbnail_key="thumbnails/abc/thumb.png",
        )

        (item,) = list_courses(client)["results"]

        assert set(item) == {
            "id",
            "slug",
            "title",
            "description",
            "price_cents",
            "thumbnail_url",
            "rating_average",
            "rating_count",
        }
        assert item["price_cents"] == 14900
        assert item["thumbnail_url"] == "https://cdn.example.com/thumbnails/abc/thumb.png"

    def test_a_course_without_a_thumbnail_has_a_blank_url(self, client):
        make_course("foundations")

        (item,) = list_courses(client)["results"]

        assert item["thumbnail_url"] == ""


class TestRatings:
    def test_a_course_with_no_reviews_has_no_average(self, client):
        make_course("unreviewed")

        item = by_slug(list_courses(client))["unreviewed"]

        assert item["rating_average"] is None
        assert item["rating_count"] == 0

    def test_ignores_hidden_reviews(self, client):
        course = make_course("reviewed")
        review(course, 5)
        review(course, 4)
        review(course, 1, status=ReviewStatus.HIDDEN)

        item = by_slug(list_courses(client))["reviewed"]

        assert item["rating_average"] == pytest.approx(4.5)
        assert item["rating_count"] == 2

    def test_only_hidden_reviews_count_as_none(self, client):
        review(make_course("hidden-only"), 1, status=ReviewStatus.HIDDEN)

        item = by_slug(list_courses(client))["hidden-only"]

        assert item["rating_average"] is None
        assert item["rating_count"] == 0

    def test_does_not_query_per_course(self, client, django_assert_num_queries):
        for i in range(3):
            review(make_course(f"course-{i}"), 5)

        # One count for the paginator, one page of annotated courses.
        with django_assert_num_queries(2):
            list_courses(client)


class TestAccess:
    def test_needs_no_token(self, client):
        make_course("published-course")
        assert len(list_courses(client)["results"]) == 1

    def test_ignores_an_invalid_token(self, client):
        make_course("published-course")
        body = list_courses(client, Authorization="Bearer not-a-real-token")
        assert len(body["results"]) == 1

    def test_ignores_a_suspended_users_token(self, client, monkeypatch):
        User.objects.create_user(
            email="ada@example.com", clerk_user_id="user_2abcDEF", status=UserStatus.SUSPENDED
        )
        monkeypatch.setattr(
            ClerkAuthentication, "decode_token", lambda self, token: {"sub": "user_2abcDEF"}
        )
        make_course("published-course")

        body = list_courses(client, Authorization="Bearer stub-token")

        assert len(body["results"]) == 1
