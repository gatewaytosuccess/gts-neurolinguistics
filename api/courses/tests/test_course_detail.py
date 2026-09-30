import pytest
from django.urls import reverse

from courses.models import Course, CourseStatus, Lesson, Module
from reviews.models import Review, ReviewStatus
from users.models import User

pytestmark = pytest.mark.django_db


def make_course(slug, status=CourseStatus.PUBLISHED, **fields):
    fields.setdefault("title", slug.replace("-", " ").title())
    fields.setdefault("price_cents", 12900)
    return Course.objects.create(slug=slug, status=status, **fields)


def make_module(course, title, position=None):
    if position is None:
        position = course.modules.count() + 1
    return Module.objects.create(course=course, title=title, position=position)


def make_lesson(module, title, position=None, **fields):
    if position is None:
        position = module.lessons.count() + 1
    return Lesson.objects.create(module=module, title=title, position=position, **fields)


def get_course(client, slug, **headers):
    return client.get(reverse("course-detail", kwargs={"slug": slug}), headers=headers)


def lesson_payload(client, slug="foundations"):
    (module,) = get_course(client, slug).json()["modules"]
    (lesson,) = module["lessons"]
    return lesson


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
    def test_extends_the_list_item(self, client):
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
        detail = get_course(client, "foundations").json()

        assert {key: detail[key] for key in list_item} == list_item
        assert set(detail) - set(list_item) == {
            "module_count",
            "lesson_count",
            "preview_lesson_count",
            "duration_seconds",
            "modules",
        }

    def test_the_list_carries_no_curriculum(self, client):
        make_lesson(make_module(make_course("foundations"), "Welcome"), "Orientation")

        (list_item,) = client.get(reverse("course-list")).json()["results"]

        assert "modules" not in list_item
        assert "lesson_count" not in list_item


class TestCurriculum:
    def test_nests_modules_and_lessons(self, client):
        course = make_course("foundations")
        module = make_module(course, "Anatomy")
        lesson = make_lesson(module, "Broca", duration_seconds=600, is_preview=True)

        body = get_course(client, "foundations").json()

        assert body["modules"] == [
            {
                "id": str(module.pk),
                "title": "Anatomy",
                "position": 1,
                "lesson_count": 1,
                "lessons": [
                    {
                        "id": str(lesson.pk),
                        "title": "Broca",
                        "position": 1,
                        "duration_seconds": 600,
                        "is_preview": True,
                        "kinds": [],
                    }
                ],
            }
        ]

    def test_orders_modules_and_lessons_by_position(self, client):
        course = make_course("foundations")
        second = make_module(course, "Second", position=2)
        first = make_module(course, "First", position=1)
        make_lesson(first, "1.2", position=2)
        make_lesson(first, "1.1", position=1)
        make_lesson(second, "2.1", position=1)

        modules = get_course(client, "foundations").json()["modules"]

        assert [m["title"] for m in modules] == ["First", "Second"]
        assert [lesson["title"] for lesson in modules[0]["lessons"]] == ["1.1", "1.2"]

    def test_counts_modules_lessons_and_previews(self, client):
        course = make_course("foundations")
        welcome = make_module(course, "Welcome")
        make_lesson(welcome, "Orientation", is_preview=True)
        make_lesson(welcome, "Vocabulary")
        anatomy = make_module(course, "Anatomy")
        make_lesson(anatomy, "Broca", is_preview=True)
        make_module(course, "Coming soon")

        body = get_course(client, "foundations").json()

        assert body["module_count"] == 3
        assert body["lesson_count"] == 3
        assert body["preview_lesson_count"] == 2
        assert [m["lesson_count"] for m in body["modules"]] == [2, 1, 0]

    def test_a_course_without_modules_has_an_empty_curriculum(self, client):
        make_course("foundations")

        body = get_course(client, "foundations").json()

        assert body["modules"] == []
        assert body["module_count"] == 0
        assert body["lesson_count"] == 0
        assert body["preview_lesson_count"] == 0
        assert body["duration_seconds"] is None


class TestDuration:
    def make_lessons(self, *durations):
        course = make_course("foundations")
        welcome = make_module(course, "Welcome")
        anatomy = make_module(course, "Anatomy")
        for i, duration in enumerate(durations):
            make_lesson(welcome if i % 2 else anatomy, f"Lesson {i}", duration_seconds=duration)

    def test_sums_every_lesson_across_modules(self, client):
        self.make_lessons(600, 300, 90)

        assert get_course(client, "foundations").json()["duration_seconds"] == 990

    def test_sums_only_the_known_durations(self, client):
        self.make_lessons(600, None, 90)

        body = get_course(client, "foundations").json()

        assert body["duration_seconds"] == 690
        durations = [lesson["duration_seconds"] for m in body["modules"] for lesson in m["lessons"]]
        assert sorted(durations, key=lambda d: d or 0) == [None, 90, 600]

    def test_is_null_when_no_lesson_has_one(self, client):
        self.make_lessons(None, None)

        assert get_course(client, "foundations").json()["duration_seconds"] is None


class TestKinds:
    def make_lesson(self, **fields):
        make_lesson(make_module(make_course("foundations"), "Welcome"), "Broca", **fields)

    def test_an_empty_lesson_has_none(self, client):
        self.make_lesson()

        assert lesson_payload(client)["kinds"] == []

    @pytest.mark.parametrize(
        ("fields", "kinds"),
        [
            ({"video_key": "lessons/a/v.mp4"}, ["video"]),
            ({"slides_key": "lessons/a/s.pdf"}, ["slides"]),
            ({"body": "# Notes"}, ["text"]),
        ],
    )
    def test_each_kind_alone(self, client, fields, kinds):
        self.make_lesson(**fields)

        assert lesson_payload(client)["kinds"] == kinds

    def test_lists_every_kind_in_order(self, client):
        self.make_lesson(body="# Notes", slides_key="lessons/a/s.pdf", video_key="lessons/a/v.mp4")

        assert lesson_payload(client)["kinds"] == ["video", "slides", "text"]


class TestPrivacy:
    def test_leaks_no_keys_urls_or_bodies(self, client):
        course = make_course("foundations")
        make_lesson(
            make_module(course, "Welcome"),
            "Broca",
            video_key="lessons/secret/video.mp4",
            slides_key="lessons/secret/slides.pdf",
            body="Members-only notes",
        )

        response = get_course(client, "foundations")
        lesson = lesson_payload(client)

        assert set(lesson) == {
            "id",
            "title",
            "position",
            "duration_seconds",
            "is_preview",
            "kinds",
        }
        content = response.content.decode()
        assert "lessons/secret" not in content
        assert "Members-only notes" not in content
        assert "X-Amz" not in content


class TestQueries:
    def test_does_not_query_per_module_or_lesson(self, client, django_assert_num_queries):
        course = make_course("foundations")
        for m in range(3):
            module = make_module(course, f"Module {m}")
            for n in range(3):
                make_lesson(module, f"Lesson {m}.{n}", body="Notes")

        # The course, its modules, their lessons.
        with django_assert_num_queries(3):
            get_course(client, "foundations")


class TestAccess:
    def test_ignores_an_invalid_token(self, client):
        make_course("foundations")

        response = get_course(client, "foundations", Authorization="Bearer not-a-real-token")

        assert response.status_code == 200
