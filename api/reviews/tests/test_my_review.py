import json

import pytest
from django.urls import reverse

from courses.models import Course, CourseStatus
from enrollments.models import Enrollment, EnrollmentSource, EnrollmentStatus
from reviews.models import Review, ReviewStatus
from users.authentication import ClerkAuthentication
from users.models import User, UserStatus

pytestmark = pytest.mark.django_db


def make_course(slug="foundations", status=CourseStatus.PUBLISHED):
    return Course.objects.create(slug=slug, title=slug.title(), price_cents=12900, status=status)


def enroll(user, course, **fields):
    fields.setdefault("source", EnrollmentSource.MANUAL)
    return Enrollment.objects.create(user=user, course=course, **fields)


@pytest.fixture
def ada():
    return User.objects.create_user(
        email="ada@example.com", name="Ada Lovelace", clerk_user_id="user_2abcDEF"
    )


@pytest.fixture
def signed_in(monkeypatch):
    """Stubs only token verification; the status check runs for real."""
    monkeypatch.setattr(
        ClerkAuthentication, "decode_token", lambda self, token: {"sub": "user_2abcDEF"}
    )


@pytest.fixture
def course():
    return make_course()


@pytest.fixture
def enrolled(ada, course):
    return enroll(ada, course)


AUTH = {"Authorization": "Bearer stub"}


def url(slug="foundations"):
    return reverse("course-review-mine", kwargs={"slug": slug})


def get_mine(client, slug="foundations"):
    return client.get(url(slug), headers=AUTH)


def put_mine(client, payload, slug="foundations"):
    return client.put(
        url(slug), data=json.dumps(payload), content_type="application/json", headers=AUTH
    )


def delete_mine(client, slug="foundations"):
    return client.delete(url(slug), headers=AUTH)


class TestAccess:
    @pytest.mark.parametrize("method", ["get", "put", "delete"])
    def test_rejects_a_request_with_no_token(self, client, course, method):
        assert getattr(client, method)(url()).status_code == 401

    def test_rejects_a_suspended_account(self, client, ada, signed_in, enrolled):
        User.objects.filter(pk=ada.pk).update(status=UserStatus.SUSPENDED)

        assert put_mine(client, {"rating": 5}).status_code == 401
        assert not Review.objects.exists()

    @pytest.mark.parametrize("send", [get_mine, delete_mine])
    def test_a_draft_is_not_found(self, client, ada, signed_in, send):
        draft = make_course("draft-course", status=CourseStatus.DRAFT)
        Review.objects.create(user=ada, course=draft, rating=4)

        assert send(client, "draft-course").status_code == 404
        assert Review.objects.filter(course=draft).exists()

    def test_putting_on_a_draft_is_not_found(self, client, ada, signed_in):
        draft = make_course("draft-course", status=CourseStatus.DRAFT)
        enroll(ada, draft)

        assert put_mine(client, {"rating": 5}, "draft-course").status_code == 404
        assert not Review.objects.exists()

    @pytest.mark.parametrize("send", [get_mine, delete_mine])
    def test_an_unknown_slug_is_not_found(self, client, ada, signed_in, send):
        assert send(client, "no-such-course").status_code == 404

    def test_putting_on_an_unknown_slug_is_not_found(self, client, ada, signed_in):
        assert put_mine(client, {"rating": 5}, "no-such-course").status_code == 404


class TestEligibility:
    def test_refuses_someone_not_enrolled(self, client, ada, signed_in, course):
        response = put_mine(client, {"rating": 5})

        assert response.status_code == 403
        assert response.json()["detail"]
        assert not Review.objects.exists()

    def test_refuses_a_revoked_enrollment(self, client, ada, signed_in, course):
        enroll(ada, course, status=EnrollmentStatus.REVOKED)

        assert put_mine(client, {"rating": 5}).status_code == 403
        assert not Review.objects.exists()

    def test_refuses_a_revoked_learner_editing_their_review(self, client, ada, signed_in, course):
        enroll(ada, course, status=EnrollmentStatus.REVOKED)
        review = Review.objects.create(user=ada, course=course, rating=2, body="Before.")

        assert put_mine(client, {"rating": 5, "body": "After."}).status_code == 403
        review.refresh_from_db()
        assert (review.rating, review.body) == (2, "Before.")

    def test_an_enrollment_in_another_course_does_not_count(self, client, ada, signed_in, course):
        enroll(ada, make_course("other-course"))

        assert put_mine(client, {"rating": 5}).status_code == 403

    @pytest.mark.parametrize("source", EnrollmentSource.values)
    def test_accepts_an_active_enrollment_of_any_source(
        self, client, ada, signed_in, course, source
    ):
        enroll(ada, course, source=source)

        assert put_mine(client, {"rating": 5}).status_code == 201


class TestCreateAndReplace:
    def test_creates_a_review(self, client, ada, signed_in, course, enrolled):
        response = put_mine(client, {"rating": 4, "body": "Clear and useful."})

        assert response.status_code == 201
        review = Review.objects.get()
        assert (review.user, review.course) == (ada, course)
        assert (review.rating, review.body) == (4, "Clear and useful.")
        assert review.status == ReviewStatus.PUBLISHED
        assert response.json()["id"] == str(review.id)

    def test_a_second_put_replaces_the_review(self, client, ada, signed_in, enrolled):
        first = put_mine(client, {"rating": 2, "body": "Before."}).json()

        response = put_mine(client, {"rating": 5, "body": "After."})

        assert response.status_code == 200
        review = Review.objects.get()
        assert str(review.id) == first["id"]
        assert (review.rating, review.body) == (5, "After.")

    def test_leaving_out_the_body_saves_it_blank(self, client, ada, signed_in, enrolled):
        put_mine(client, {"rating": 3, "body": "Words."})

        assert put_mine(client, {"rating": 3}).status_code == 200
        assert Review.objects.get().body == ""

    def test_a_blank_body_is_allowed(self, client, ada, signed_in, enrolled):
        assert put_mine(client, {"rating": 3, "body": ""}).status_code == 201

    def test_a_hidden_review_stays_hidden(self, client, ada, signed_in, course, enrolled):
        Review.objects.create(user=ada, course=course, rating=1, status=ReviewStatus.HIDDEN)

        response = put_mine(client, {"rating": 5, "body": "Changed my mind."})

        assert response.status_code == 200
        assert response.json()["status"] == "hidden"
        assert Review.objects.get().status == ReviewStatus.HIDDEN

    def test_status_cannot_be_set(self, client, ada, signed_in, course, enrolled):
        Review.objects.create(user=ada, course=course, rating=1, status=ReviewStatus.HIDDEN)

        put_mine(client, {"rating": 5, "status": "published"})

        assert Review.objects.get().status == ReviewStatus.HIDDEN

    def test_leaves_other_reviews_alone(self, client, ada, signed_in, course, enrolled):
        grace = User.objects.create_user(email="grace@example.com")
        theirs = Review.objects.create(user=grace, course=course, rating=1, body="Theirs.")

        put_mine(client, {"rating": 5})

        theirs.refresh_from_db()
        assert (theirs.rating, theirs.body) == (1, "Theirs.")
        assert Review.objects.count() == 2


class TestValidation:
    @pytest.mark.parametrize("rating", [0, 6, -1, "five", None])
    def test_refuses_a_rating_outside_one_to_five(self, client, ada, signed_in, enrolled, rating):
        response = put_mine(client, {"rating": rating})

        assert response.status_code == 400
        assert response.json() == {"rating": ["Choose a rating from 1 to 5 stars."]}
        assert not Review.objects.exists()

    def test_requires_a_rating(self, client, ada, signed_in, enrolled):
        response = put_mine(client, {"body": "No stars."})

        assert response.status_code == 400
        assert response.json() == {"rating": ["Choose a rating from 1 to 5 stars."]}

    def test_accepts_a_body_of_two_thousand_characters(self, client, ada, signed_in, enrolled):
        assert put_mine(client, {"rating": 4, "body": "a" * 2000}).status_code == 201

    def test_refuses_a_body_over_two_thousand_characters(self, client, ada, signed_in, enrolled):
        response = put_mine(client, {"rating": 4, "body": "a" * 2001})

        assert response.status_code == 400
        assert response.json() == {"body": ["Keep your review to 2,000 characters or fewer."]}
        assert not Review.objects.exists()

    def test_a_refused_edit_leaves_the_review_alone(self, client, ada, signed_in, enrolled):
        put_mine(client, {"rating": 4, "body": "Kept."})

        assert put_mine(client, {"rating": 9, "body": "Lost."}).status_code == 400
        review = Review.objects.get()
        assert (review.rating, review.body) == (4, "Kept.")


class TestRetrieve:
    def test_returns_the_requesters_review(self, client, ada, signed_in, course):
        review = Review.objects.create(user=ada, course=course, rating=4, body="Mine.")

        response = get_mine(client)

        assert response.status_code == 200
        payload = response.json()
        assert set(payload) == {"id", "rating", "body", "status", "created_at", "updated_at"}
        assert payload["id"] == str(review.id)
        assert (payload["rating"], payload["body"], payload["status"]) == (4, "Mine.", "published")

    def test_returns_a_hidden_review(self, client, ada, signed_in, course):
        Review.objects.create(user=ada, course=course, rating=4, status=ReviewStatus.HIDDEN)

        response = get_mine(client)

        assert response.status_code == 200
        assert response.json()["status"] == "hidden"

    def test_is_not_found_with_no_review(self, client, ada, signed_in, course):
        grace = User.objects.create_user(email="grace@example.com")
        Review.objects.create(user=grace, course=course, rating=4)

        assert get_mine(client).status_code == 404

    def test_needs_no_enrollment(self, client, ada, signed_in, course):
        enroll(ada, course, status=EnrollmentStatus.REVOKED)
        Review.objects.create(user=ada, course=course, rating=4)

        assert get_mine(client).status_code == 200


class TestDelete:
    def test_deletes_the_review(self, client, ada, signed_in, course, enrolled):
        Review.objects.create(user=ada, course=course, rating=4)

        response = delete_mine(client)

        assert response.status_code == 204
        assert not Review.objects.exists()

    def test_a_revoked_learner_may_delete(self, client, ada, signed_in, course):
        enroll(ada, course, status=EnrollmentStatus.REVOKED)
        Review.objects.create(user=ada, course=course, rating=4)

        assert delete_mine(client).status_code == 204
        assert not Review.objects.exists()

    def test_is_not_found_with_no_review(self, client, ada, signed_in, course, enrolled):
        assert delete_mine(client).status_code == 404

    def test_leaves_other_reviews_alone(self, client, ada, signed_in, course):
        grace = User.objects.create_user(email="grace@example.com")
        Review.objects.create(user=grace, course=course, rating=4)
        Review.objects.create(user=ada, course=course, rating=4)

        delete_mine(client)

        assert list(Review.objects.values_list("user", flat=True)) == [grace.pk]
