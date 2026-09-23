import uuid

import pytest
from django.db import connection
from django.urls import reverse

from courses.models import Course, Lesson, Module
from enrollments.models import LessonProgress
from users.authentication import ClerkAuthentication
from users.models import Role, User

pytestmark = pytest.mark.django_db

AUTH = {"Authorization": "Bearer stub"}


def make_course(slug="foundations"):
    return Course.objects.create(slug=slug, title=slug.title(), price_cents=12900)


def make_module(course, title, position=None):
    if position is None:
        position = course.modules.count() + 1
    return Module.objects.create(course=course, title=title, position=position)


def make_lesson(module, title, position=None, **fields):
    if position is None:
        position = module.lessons.count() + 1
    return Lesson.objects.create(module=module, title=title, position=position, **fields)


def make_learner(n):
    return User.objects.create_user(email=f"learner{n}@example.com", clerk_user_id=f"user_{n}")


def give_progress(lesson, *learners):
    for learner in learners:
        LessonProgress.objects.create(user=learner, lesson=lesson)


def module_titles(course):
    """Titles in position order, after checking the positions run 1…n with no gaps."""
    # Position constraints are deferred to commit, which a test never reaches.
    with connection.cursor() as cursor:
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
    modules = list(Module.objects.filter(course=course).order_by("position"))
    assert [m.position for m in modules] == list(range(1, len(modules) + 1))
    return [m.title for m in modules]


def lesson_titles(module):
    """Titles in position order, after checking the positions run 1…n with no gaps."""
    with connection.cursor() as cursor:
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
    lessons = list(Lesson.objects.filter(module=module).order_by("position"))
    assert [lesson.position for lesson in lessons] == list(range(1, len(lessons) + 1))
    return [lesson.title for lesson in lessons]


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


@pytest.fixture
def course():
    return make_course()


@pytest.fixture
def modules(course):
    """Modules A, B and C, each with lessons 1, 2 and 3."""
    built = {}
    for title in "ABC":
        module = make_module(course, title)
        for n in (1, 2, 3):
            make_lesson(module, f"{title}{n}")
        built[title] = module
    return built


def get(client, name, pk):
    return client.get(reverse(name, kwargs={"pk": pk}), headers=AUTH)


def post(client, name, pk, **body):
    return client.post(
        reverse(name, kwargs={"pk": pk}), body, content_type="application/json", headers=AUTH
    )


def patch(client, name, pk, **body):
    return client.patch(
        reverse(name, kwargs={"pk": pk}), body, content_type="application/json", headers=AUTH
    )


def delete(client, name, pk):
    return client.delete(reverse(name, kwargs={"pk": pk}), headers=AUTH)


def get_curriculum(client, course):
    response = get(client, "admin-course-curriculum", course.pk)
    assert response.status_code == 200, response.json()
    return response.json()


def move_module(client, module, **body):
    return post(client, "admin-module-move", module.pk, **body)


def move_lesson(client, lesson, **body):
    return post(client, "admin-lesson-move", lesson.pk, **body)


class TestAccess:
    @pytest.fixture
    def requests(self, client, modules):
        course, module, lesson = modules["A"].course, modules["A"], modules["A"].lessons.first()
        return [
            lambda: get(client, "admin-course-curriculum", course.pk),
            lambda: post(client, "admin-module-create", course.pk, title="New"),
            lambda: patch(client, "admin-module", module.pk, title="Renamed"),
            lambda: delete(client, "admin-module", module.pk),
            lambda: move_module(client, module, position=3),
            lambda: post(client, "admin-lesson-create", module.pk, title="New"),
            lambda: delete(client, "admin-lesson", lesson.pk),
            lambda: move_lesson(client, lesson, position=3),
        ]

    def test_rejects_requests_with_no_token(self, course, requests):
        assert [request().status_code for request in requests] == [401] * len(requests)

    def test_forbids_a_learner(self, course, learner, requests):
        assert [request().status_code for request in requests] == [403] * len(requests)
        assert module_titles(course) == ["A", "B", "C"]
        assert lesson_titles(Module.objects.get(title="A")) == ["A1", "A2", "A3"]


class TestCurriculum:
    def test_lists_modules_and_lessons_in_order(self, client, admin, course):
        second = make_module(course, "Second", position=2)
        first = make_module(course, "First", position=1)
        make_lesson(first, "Lesson 1.2", position=2, body="Text")
        make_lesson(first, "Lesson 1.1", position=1, is_preview=True)

        body = get_curriculum(client, course)

        assert [m["title"] for m in body] == ["First", "Second"]
        assert [m["id"] for m in body] == [str(first.pk), str(second.pk)]
        assert [lesson["title"] for lesson in body[0]["lessons"]] == ["Lesson 1.1", "Lesson 1.2"]
        assert body[1]["lessons"] == []

    def test_returns_the_lesson_fields(self, client, admin, course):
        lesson = make_lesson(make_module(course, "Only"), "Intro", is_preview=True)

        assert get_curriculum(client, course)[0]["lessons"] == [
            {
                "id": str(lesson.pk),
                "title": "Intro",
                "position": 1,
                "is_empty": True,
                "is_preview": True,
                "learners_with_progress": 0,
            }
        ]

    @pytest.mark.parametrize("part", ["video_key", "slides_key", "body"])
    def test_a_lesson_with_any_part_is_not_empty(self, client, admin, course, part):
        make_lesson(make_module(course, "Only"), "Intro", **{part: "x"})

        assert get_curriculum(client, course)[0]["lessons"][0]["is_empty"] is False

    def test_counts_learners_with_progress(self, client, admin, course, modules):
        ann, bob, cat = make_learner(1), make_learner(2), make_learner(3)
        a1, a2, _ = modules["A"].lessons.order_by("position")
        give_progress(a1, ann, bob, cat)
        give_progress(a2, ann)
        give_progress(modules["B"].lessons.first(), bob)
        # Another course's progress is not counted.
        give_progress(make_lesson(make_module(make_course("other"), "X"), "X1"), ann)

        body = get_curriculum(client, course)

        a, b, c = body
        assert [lesson["learners_with_progress"] for lesson in a["lessons"]] == [3, 1, 0]
        # A learner with progress on several lessons counts once for the module.
        assert a["learners_with_progress"] == 3
        assert b["learners_with_progress"] == 1
        assert c["learners_with_progress"] == 0

    def test_a_course_with_no_modules_is_empty(self, client, admin, course):
        assert get_curriculum(client, course) == []

    def test_an_unknown_course_is_not_found(self, client, admin):
        assert get(client, "admin-course-curriculum", uuid.uuid4()).status_code == 404

    def test_is_not_paginated(self, client, admin, course):
        for n in range(25):
            make_module(course, f"Module {n}")

        assert len(get_curriculum(client, course)) == 25


class TestAddModule:
    def test_appends_the_module(self, client, admin, course, modules):
        response = post(client, "admin-module-create", course.pk, title="D")

        assert response.status_code == 201
        assert response.json()["title"] == "D"
        assert response.json()["position"] == 4
        assert module_titles(course) == ["A", "B", "C", "D"]

    def test_the_first_module_is_at_position_1(self, client, admin, course):
        response = post(client, "admin-module-create", course.pk, title="First")

        assert response.json()["position"] == 1

    def test_ignores_a_position_in_the_body(self, client, admin, course, modules):
        response = post(client, "admin-module-create", course.pk, title="D", position=1)

        assert response.json()["position"] == 4
        assert module_titles(course) == ["A", "B", "C", "D"]

    @pytest.mark.parametrize("body", [{}, {"title": ""}])
    def test_requires_a_title(self, client, admin, course, body):
        response = post(client, "admin-module-create", course.pk, **body)

        assert response.status_code == 400
        assert "title" in response.json()
        assert not course.modules.exists()

    def test_an_unknown_course_is_not_found(self, client, admin):
        assert post(client, "admin-module-create", uuid.uuid4(), title="X").status_code == 404


class TestRenameModule:
    def test_renames_it(self, client, admin, course, modules):
        response = patch(client, "admin-module", modules["B"].pk, title="Renamed")

        assert response.status_code == 200
        assert response.json()["title"] == "Renamed"
        assert module_titles(course) == ["A", "Renamed", "C"]

    def test_ignores_a_position_in_the_body(self, client, admin, course, modules):
        patch(client, "admin-module", modules["B"].pk, title="B", position=1)

        assert module_titles(course) == ["A", "B", "C"]

    def test_refuses_a_blank_title(self, client, admin, course, modules):
        response = patch(client, "admin-module", modules["B"].pk, title="")

        assert response.status_code == 400
        assert module_titles(course) == ["A", "B", "C"]

    def test_get_is_not_allowed(self, client, admin, modules):
        assert get(client, "admin-module", modules["A"].pk).status_code == 405

    def test_an_unknown_module_is_not_found(self, client, admin):
        assert patch(client, "admin-module", uuid.uuid4(), title="X").status_code == 404


class TestDeleteModule:
    def test_renumbers_the_remaining_modules(self, client, admin, course, modules):
        response = delete(client, "admin-module", modules["A"].pk)

        assert response.status_code == 204
        assert module_titles(course) == ["B", "C"]

    def test_deletes_its_lessons_and_their_progress(self, client, admin, course, modules):
        learner = make_learner(1)
        give_progress(modules["A"].lessons.first(), learner)
        give_progress(modules["B"].lessons.first(), learner)

        delete(client, "admin-module", modules["A"].pk)

        assert not Lesson.objects.filter(title__startswith="A").exists()
        assert list(LessonProgress.objects.values_list("lesson__title", flat=True)) == ["B1"]

    def test_leaves_other_courses_alone(self, client, admin, course, modules):
        other = make_course("other")
        make_module(other, "X")
        make_module(other, "Y")

        delete(client, "admin-module", modules["B"].pk)

        assert module_titles(other) == ["X", "Y"]

    def test_an_unknown_module_is_not_found(self, client, admin):
        assert delete(client, "admin-module", uuid.uuid4()).status_code == 404


class TestMoveModule:
    @pytest.mark.parametrize(
        "title, position, expected",
        [
            ("B", 1, ["B", "A", "C"]),  # up
            ("B", 3, ["A", "C", "B"]),  # down
            ("C", 1, ["C", "A", "B"]),  # to first
            ("A", 3, ["B", "C", "A"]),  # to last
            ("B", 2, ["A", "B", "C"]),  # in place
            ("A", 99, ["B", "C", "A"]),  # clamped to last
            ("C", 0, ["C", "A", "B"]),  # clamped to first
            ("C", -5, ["C", "A", "B"]),  # clamped to first
        ],
    )
    def test_moves_it(self, client, admin, course, modules, title, position, expected):
        response = move_module(client, modules[title], position=position)

        assert response.status_code == 200
        assert response.json()["position"] == expected.index(title) + 1
        assert module_titles(course) == expected

    def test_leaves_its_lessons_in_place(self, client, admin, course, modules):
        move_module(client, modules["A"], position=3)

        assert lesson_titles(modules["A"]) == ["A1", "A2", "A3"]

    @pytest.mark.parametrize("body", [{}, {"position": "first"}, {"position": None}])
    def test_requires_a_whole_number_position(self, client, admin, course, modules, body):
        response = move_module(client, modules["B"], **body)

        assert response.status_code == 400
        assert "position" in response.json()
        assert module_titles(course) == ["A", "B", "C"]

    def test_an_unknown_module_is_not_found(self, client, admin):
        response = post(client, "admin-module-move", uuid.uuid4(), position=1)

        assert response.status_code == 404


class TestAddLesson:
    def test_appends_an_empty_lesson(self, client, admin, modules):
        response = post(client, "admin-lesson-create", modules["B"].pk, title="B4")

        assert response.status_code == 201
        body = response.json()
        assert body["title"] == "B4"
        assert body["position"] == 4
        assert body["module"] == str(modules["B"].pk)
        assert body["is_empty"] is True
        assert body["is_preview"] is False
        assert lesson_titles(modules["B"]) == ["B1", "B2", "B3", "B4"]

    def test_ignores_content_in_the_body(self, client, admin, course):
        module = make_module(course, "Only")

        post(client, "admin-lesson-create", module.pk, title="New", body="Text", is_preview=True)

        lesson = module.lessons.get()
        assert lesson.is_empty
        assert not lesson.is_preview

    @pytest.mark.parametrize("body", [{}, {"title": ""}])
    def test_requires_a_title(self, client, admin, course, body):
        module = make_module(course, "Only")

        response = post(client, "admin-lesson-create", module.pk, **body)

        assert response.status_code == 400
        assert "title" in response.json()
        assert not module.lessons.exists()

    def test_an_unknown_module_is_not_found(self, client, admin):
        assert post(client, "admin-lesson-create", uuid.uuid4(), title="X").status_code == 404


class TestDeleteLesson:
    def test_renumbers_the_remaining_siblings(self, client, admin, modules):
        response = delete(client, "admin-lesson", modules["A"].lessons.get(title="A1").pk)

        assert response.status_code == 204
        assert lesson_titles(modules["A"]) == ["A2", "A3"]

    def test_deletes_its_progress(self, client, admin, modules):
        learner = make_learner(1)
        a1, a2 = modules["A"].lessons.get(title="A1"), modules["A"].lessons.get(title="A2")
        give_progress(a1, learner)
        give_progress(a2, learner)

        delete(client, "admin-lesson", a1.pk)

        assert list(LessonProgress.objects.values_list("lesson", flat=True)) == [a2.pk]

    def test_leaves_other_modules_alone(self, client, admin, modules):
        delete(client, "admin-lesson", modules["A"].lessons.get(title="A2").pk)

        assert lesson_titles(modules["B"]) == ["B1", "B2", "B3"]

    def test_an_unknown_lesson_is_not_found(self, client, admin):
        assert delete(client, "admin-lesson", uuid.uuid4()).status_code == 404


class TestMoveLesson:
    @pytest.mark.parametrize(
        "title, position, expected",
        [
            ("A2", 1, ["A2", "A1", "A3"]),  # up
            ("A2", 3, ["A1", "A3", "A2"]),  # down
            ("A3", 1, ["A3", "A1", "A2"]),  # to first
            ("A1", 3, ["A2", "A3", "A1"]),  # to last
            ("A2", 2, ["A1", "A2", "A3"]),  # in place
            ("A1", 99, ["A2", "A3", "A1"]),  # clamped to last
            ("A3", 0, ["A3", "A1", "A2"]),  # clamped to first
            ("A3", -5, ["A3", "A1", "A2"]),  # clamped to first
        ],
    )
    def test_moves_it_within_its_module(self, client, admin, modules, title, position, expected):
        lesson = modules["A"].lessons.get(title=title)

        response = move_lesson(client, lesson, position=position)

        assert response.status_code == 200
        assert response.json()["position"] == expected.index(title) + 1
        assert lesson_titles(modules["A"]) == expected

    @pytest.mark.parametrize(
        "position, expected",
        [
            (1, ["A2", "B1", "B2", "B3"]),
            (2, ["B1", "A2", "B2", "B3"]),
            (4, ["B1", "B2", "B3", "A2"]),
            (99, ["B1", "B2", "B3", "A2"]),
            (0, ["A2", "B1", "B2", "B3"]),
        ],
    )
    def test_moves_it_to_another_module(self, client, admin, modules, position, expected):
        lesson = modules["A"].lessons.get(title="A2")

        response = move_lesson(client, lesson, module_id=str(modules["B"].pk), position=position)

        assert response.status_code == 200
        assert response.json()["module"] == str(modules["B"].pk)
        assert response.json()["position"] == expected.index("A2") + 1
        assert lesson_titles(modules["A"]) == ["A1", "A3"]
        assert lesson_titles(modules["B"]) == expected

    def test_without_a_position_it_goes_last_in_the_other_module(self, client, admin, modules):
        lesson = modules["A"].lessons.get(title="A1")

        move_lesson(client, lesson, module_id=str(modules["C"].pk))

        assert lesson_titles(modules["A"]) == ["A2", "A3"]
        assert lesson_titles(modules["C"]) == ["C1", "C2", "C3", "A1"]

    def test_moves_it_to_an_empty_module(self, client, admin, course, modules):
        empty = make_module(course, "D")

        move_lesson(client, modules["A"].lessons.get(title="A3"), module_id=str(empty.pk))

        assert lesson_titles(modules["A"]) == ["A1", "A2"]
        assert lesson_titles(empty) == ["A3"]

    def test_its_own_module_id_moves_it_within_the_module(self, client, admin, modules):
        lesson = modules["A"].lessons.get(title="A1")

        move_lesson(client, lesson, module_id=str(modules["A"].pk), position=2)

        assert lesson_titles(modules["A"]) == ["A2", "A1", "A3"]

    def test_keeps_its_progress(self, client, admin, modules):
        lesson = modules["A"].lessons.get(title="A1")
        give_progress(lesson, make_learner(1))

        move_lesson(client, lesson, module_id=str(modules["B"].pk))

        assert LessonProgress.objects.get().lesson_id == lesson.pk

    def test_refuses_a_module_of_another_course(self, client, admin, modules):
        other = make_module(make_course("other"), "X")
        make_lesson(other, "X1")
        lesson = modules["A"].lessons.get(title="A1")

        response = move_lesson(client, lesson, module_id=str(other.pk), position=1)

        assert response.status_code == 400
        assert "module_id" in response.json()
        assert lesson_titles(modules["A"]) == ["A1", "A2", "A3"]
        assert lesson_titles(other) == ["X1"]

    def test_refuses_an_unknown_module(self, client, admin, modules):
        response = move_lesson(client, modules["A"].lessons.first(), module_id=str(uuid.uuid4()))

        assert response.status_code == 400
        assert "module_id" in response.json()

    def test_requires_a_position_or_a_module(self, client, admin, modules):
        response = move_lesson(client, modules["A"].lessons.first())

        assert response.status_code == 400
        assert "position" in response.json()

    def test_refuses_a_position_that_is_not_a_whole_number(self, client, admin, modules):
        response = move_lesson(client, modules["A"].lessons.first(), position="last")

        assert response.status_code == 400
        assert lesson_titles(modules["A"]) == ["A1", "A2", "A3"]

    def test_an_unknown_lesson_is_not_found(self, client, admin):
        assert post(client, "admin-lesson-move", uuid.uuid4(), position=1).status_code == 404
