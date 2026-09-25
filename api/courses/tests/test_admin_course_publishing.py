import uuid

import pytest
from django.db.models import ProtectedError
from django.urls import reverse

from commerce.models import Order, OrderItem, OrderStatus
from courses.models import Course, CourseStatus, Lesson, Module
from courses.publishing import publish_problems
from enrollments.models import Enrollment, EnrollmentSource, EnrollmentStatus, LessonProgress
from reviews.models import Review
from users.authentication import ClerkAuthentication
from users.models import Role, User

pytestmark = pytest.mark.django_db

AUTH = {"Authorization": "Bearer stub"}
BUCKET = "gts-thumbnails"


@pytest.fixture
def signed_in(monkeypatch):
    """Stubs only token verification; the status check runs for real."""
    monkeypatch.setattr(
        ClerkAuthentication, "decode_token", lambda self, token: {"sub": "user_2abcDEF"}
    )


@pytest.fixture
def admin(signed_in):
    return User.objects.create_user(
        email="ada@example.com", clerk_user_id="user_2abcDEF", role=Role.ADMIN
    )


@pytest.fixture
def learner(signed_in):
    return User.objects.create_user(email="ada@example.com", clerk_user_id="user_2abcDEF")


def make_learner(n=1):
    return User.objects.create_user(email=f"learner{n}@example.com", clerk_user_id=f"user_{n}")


def make_course(slug="foundations", status=CourseStatus.DRAFT):
    """A course that meets every publish rule: one module holding one lesson with a body."""
    course = Course.objects.create(
        slug=slug,
        title="Foundations",
        description="About the course.",
        price_cents=12900,
        status=status,
    )
    course.thumbnail_key = f"thumbnails/{course.pk}/cover.png"
    course.save()
    module = Module.objects.create(course=course, title="Anatomy", position=1)
    Lesson.objects.create(module=module, title="Broca", position=1, body="Text.")
    return course


def only_module(course):
    return course.modules.get()


def only_lesson(course):
    return Lesson.objects.get(module__course=course)


@pytest.fixture
def draft():
    return make_course()


@pytest.fixture
def published():
    return make_course("aphasia", status=CourseStatus.PUBLISHED)


def post(client, name, course_or_id):
    pk = getattr(course_or_id, "pk", course_or_id)
    return client.post(reverse(name, kwargs={"pk": pk}), headers=AUTH)


def publish(client, course_or_id):
    return post(client, "admin-course-publish", course_or_id)


def unpublish(client, course_or_id):
    return post(client, "admin-course-unpublish", course_or_id)


def delete_course(client, course_or_id):
    pk = getattr(course_or_id, "pk", course_or_id)
    return client.delete(reverse("admin-course-detail", kwargs={"pk": pk}), headers=AUTH)


def problems(response):
    assert response.status_code == 400, response.json()
    return response.json()["problems"]


def status_of(course):
    course.refresh_from_db()
    return course.status


class TestPublishProblems:
    def test_none_for_a_publishable_course(self, draft):
        assert publish_problems(draft) == []

    def test_a_blank_title(self, draft):
        draft.title = "  "

        assert publish_problems(draft) == ["The course has no title."]

    def test_a_price_of_zero(self, draft):
        draft.price_cents = 0

        assert publish_problems(draft) == ["The course's price must be above 0."]

    def test_a_blank_description(self, draft):
        draft.description = " \n"

        assert publish_problems(draft) == ["The course has no description."]

    def test_no_thumbnail(self, draft):
        draft.thumbnail_key = ""

        assert publish_problems(draft) == ["The course has no thumbnail."]

    def test_no_modules(self, draft):
        only_module(draft).delete()

        assert publish_problems(draft) == ["The course has no modules."]

    def test_a_module_without_lessons(self, draft):
        Module.objects.create(course=draft, title="Recovery", position=2)

        assert publish_problems(draft) == ['Module "Recovery" has no lessons.']

    def test_names_each_empty_lesson(self, draft):
        module = only_module(draft)
        Lesson.objects.create(module=module, title="Wernicke", position=2)
        Lesson.objects.create(module=module, title="Geschwind", position=3)

        assert publish_problems(draft) == [
            'Lesson "Wernicke" in "Anatomy" is empty.',
            'Lesson "Geschwind" in "Anatomy" is empty.',
        ]

    @pytest.mark.parametrize(
        "content", [{"video_key": "videos/a.mp4"}, {"slides_key": "slides/a.pdf"}, {"body": "Hi"}]
    )
    def test_any_one_part_makes_a_lesson_not_empty(self, draft, content):
        Lesson.objects.create(module=only_module(draft), title="Wernicke", position=2, **content)

        assert publish_problems(draft) == []

    def test_lists_every_problem_in_curriculum_order(self, draft):
        draft.thumbnail_key = ""
        only_lesson(draft).delete()
        second = Module.objects.create(course=draft, title="Recovery", position=2)
        Lesson.objects.create(module=second, title="Plasticity", position=1)

        assert publish_problems(draft) == [
            "The course has no thumbnail.",
            'Module "Anatomy" has no lessons.',
            'Lesson "Plasticity" in "Recovery" is empty.',
        ]


class TestAccess:
    def test_rejects_requests_with_no_token(self, client, draft):
        assert (
            client.post(reverse("admin-course-publish", kwargs={"pk": draft.pk})).status_code == 401
        )
        assert (
            client.post(reverse("admin-course-unpublish", kwargs={"pk": draft.pk})).status_code
            == 401
        )
        assert (
            client.delete(reverse("admin-course-detail", kwargs={"pk": draft.pk})).status_code
            == 401
        )

    def test_forbids_a_learner(self, client, learner, draft, published):
        assert publish(client, draft).status_code == 403
        assert unpublish(client, published).status_code == 403
        assert delete_course(client, draft).status_code == 403
        assert status_of(draft) == CourseStatus.DRAFT
        assert status_of(published) == CourseStatus.PUBLISHED
        assert Course.objects.count() == 2

    @pytest.mark.parametrize("action", [publish, unpublish, delete_course])
    def test_an_unknown_id_is_not_found(self, client, admin, action):
        assert action(client, uuid.uuid4()).status_code == 404


class TestPublish:
    def test_publishes_a_publishable_draft(self, client, admin, draft):
        response = publish(client, draft)

        assert response.status_code == 200
        assert response.json()["status"] == CourseStatus.PUBLISHED
        assert status_of(draft) == CourseStatus.PUBLISHED

    def test_the_course_joins_the_catalog(self, client, admin, draft):
        publish(client, draft)

        slugs = [course["slug"] for course in client.get(reverse("course-list")).json()["results"]]
        assert slugs == ["foundations"]

    def test_refuses_with_every_problem(self, client, admin):
        course = Course.objects.create(slug="new", title="New", price_cents=100)
        module = Module.objects.create(course=course, title="Anatomy", position=1)
        Lesson.objects.create(module=module, title="Broca", position=1)

        assert problems(publish(client, course)) == [
            "The course has no description.",
            "The course has no thumbnail.",
            'Lesson "Broca" in "Anatomy" is empty.',
        ]
        assert status_of(course) == CourseStatus.DRAFT

    def test_publishing_a_published_course_changes_nothing(self, client, admin, published):
        assert publish(client, published).status_code == 200
        assert status_of(published) == CourseStatus.PUBLISHED


class TestUnpublish:
    def test_makes_it_a_draft(self, client, admin, published):
        response = unpublish(client, published)

        assert response.status_code == 200
        assert response.json()["status"] == CourseStatus.DRAFT
        assert status_of(published) == CourseStatus.DRAFT

    def test_succeeds_even_with_problems(self, client, admin):
        course = Course.objects.create(
            slug="broken", title="Broken", price_cents=100, status=CourseStatus.PUBLISHED
        )

        assert unpublish(client, course).status_code == 200
        assert status_of(course) == CourseStatus.DRAFT

    def test_keeps_enrollments(self, client, admin, published):
        enrollment = Enrollment.objects.create(
            user=make_learner(), course=published, source=EnrollmentSource.PURCHASE
        )

        unpublish(client, published)

        enrollment.refresh_from_db()
        assert enrollment.status == EnrollmentStatus.ACTIVE

    def test_leaves_the_catalog(self, client, admin, published):
        unpublish(client, published)

        assert client.get(reverse("course-list")).json()["results"] == []


def patch(client, name, pk, **body):
    return client.patch(
        reverse(name, kwargs={"pk": pk}), body, content_type="application/json", headers=AUTH
    )


def delete(client, name, pk):
    return client.delete(reverse(name, kwargs={"pk": pk}), headers=AUTH)


class TestPublishedStaysPublishable:
    """Each edit is refused on a published course and succeeds on a draft."""

    def test_deleting_its_only_lesson(self, client, admin, published, draft):
        response = delete(client, "admin-lesson", only_lesson(published).pk)

        assert problems(response) == ['Module "Anatomy" has no lessons.']
        assert Lesson.objects.filter(module__course=published).exists()
        assert delete(client, "admin-lesson", only_lesson(draft).pk).status_code == 204

    def test_emptying_a_lessons_body(self, client, admin, published, draft):
        response = patch(client, "admin-lesson", only_lesson(published).pk, body="")

        assert problems(response) == ['Lesson "Broca" in "Anatomy" is empty.']
        assert only_lesson(published).body == "Text."
        assert patch(client, "admin-lesson", only_lesson(draft).pk, body="").status_code == 200

    def test_deleting_the_last_module(self, client, admin, published, draft):
        response = delete(client, "admin-module", only_module(published).pk)

        assert problems(response) == ["The course has no modules."]
        assert published.modules.exists()
        assert delete(client, "admin-module", only_module(draft).pk).status_code == 204

    def test_removing_the_thumbnail(self, client, admin, s3, published, draft):
        response = patch(client, "admin-course-detail", published.pk, thumbnail_key="")

        assert problems(response) == ["The course has no thumbnail."]
        published.refresh_from_db()
        assert published.thumbnail_key
        assert patch(client, "admin-course-detail", draft.pk, thumbnail_key="").status_code == 200

    def test_adding_a_module(self, client, admin, published):
        response = client.post(
            reverse("admin-module-create", kwargs={"pk": published.pk}),
            {"title": "Recovery"},
            content_type="application/json",
            headers=AUTH,
        )

        assert problems(response) == ['Module "Recovery" has no lessons.']
        assert published.modules.count() == 1

    def test_moving_a_modules_only_lesson_away(self, client, admin, published):
        first = only_module(published)
        second = Module.objects.create(course=published, title="Recovery", position=2)
        lesson = Lesson.objects.create(module=second, title="Plasticity", position=1, body="Text.")

        response = client.post(
            reverse("admin-lesson-move", kwargs={"pk": lesson.pk}),
            {"module_id": str(first.pk)},
            content_type="application/json",
            headers=AUTH,
        )

        assert problems(response) == ['Module "Recovery" has no lessons.']
        lesson.refresh_from_db()
        assert lesson.module == second

    def test_edits_that_keep_it_publishable_succeed(self, client, admin, published):
        assert patch(client, "admin-course-detail", published.pk, title="New").status_code == 200
        assert (
            patch(client, "admin-module", only_module(published).pk, title="New").status_code == 200
        )
        assert (
            patch(client, "admin-lesson", only_lesson(published).pk, body="New.").status_code == 200
        )
        assert status_of(published) == CourseStatus.PUBLISHED


def enroll(course, status=EnrollmentStatus.ACTIVE):
    return Enrollment.objects.create(
        user=make_learner(), course=course, source=EnrollmentSource.MANUAL, status=status
    )


def buy(course):
    order = Order.objects.create(
        user=make_learner(), status=OrderStatus.PAID, subtotal_cents=100, total_cents=100
    )
    return OrderItem.objects.create(order=order, course=course, unit_price_cents=100)


def review(course):
    return Review.objects.create(user=make_learner(), course=course, rating=5)


class TestDelete:
    @pytest.mark.parametrize(
        "history",
        [
            enroll,
            lambda course: enroll(course, status=EnrollmentStatus.REVOKED),
            buy,
            review,
        ],
        ids=["enrollment", "revoked enrollment", "order item", "review"],
    )
    def test_refuses_a_course_with_history(self, client, admin, draft, history):
        history(draft)

        response = delete_course(client, draft)

        assert response.status_code == 409
        assert "Unpublish" in response.json()["detail"]
        assert Course.objects.filter(pk=draft.pk).exists()

    def test_deletes_a_clean_draft_and_its_curriculum(
        self, client, admin, s3, draft, django_capture_on_commit_callbacks
    ):
        LessonProgress.objects.create(user=make_learner(), lesson=only_lesson(draft))
        s3.add_response("delete_object", {}, {"Bucket": BUCKET, "Key": draft.thumbnail_key})

        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            response = delete_course(client, draft)

        assert response.status_code == 204
        assert len(callbacks) == 1
        assert not Course.objects.exists()
        assert not Module.objects.exists()
        assert not Lesson.objects.exists()
        assert not LessonProgress.objects.exists()

    def test_a_course_without_a_thumbnail_touches_no_storage(
        self, client, admin, s3, django_capture_on_commit_callbacks
    ):
        course = Course.objects.create(slug="bare", title="Bare", price_cents=100)

        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            assert delete_course(client, course).status_code == 204

        assert callbacks == []

    def test_a_refused_delete_touches_no_storage(
        self, client, admin, s3, draft, django_capture_on_commit_callbacks
    ):
        review(draft)

        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            assert delete_course(client, draft).status_code == 409

        assert callbacks == []

    def test_a_deleted_course_leaves_the_catalog(self, client, admin, s3, published):
        assert delete_course(client, published).status_code == 204
        assert client.get(reverse("course-list")).json()["results"] == []


class TestProtectedAtTheOrm:
    @pytest.mark.parametrize(
        "history", [enroll, review, buy], ids=["enrollment", "review", "order"]
    )
    def test_deleting_a_course_with_history_raises(self, draft, history):
        history(draft)

        with pytest.raises(ProtectedError):
            draft.delete()
