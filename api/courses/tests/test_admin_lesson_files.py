import base64
import json
import logging
import uuid
from urllib.parse import parse_qs, urlparse

import pytest
from django.urls import reverse

from courses.models import Course, CourseStatus, Lesson, Module
from users.authentication import ClerkAuthentication
from users.models import Role, User

pytestmark = pytest.mark.django_db

AUTH = {"Authorization": "Bearer stub"}
BUCKET = "gts-private"


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


def make_lesson(course=None, title="Broca", **fields):
    if course is None:
        course = Course.objects.create(slug="foundations", title="Foundations", price_cents=12900)
    module = course.modules.first() or Module.objects.create(
        course=course, title="Anatomy", position=1
    )
    return Lesson.objects.create(
        module=module, title=title, position=module.lessons.count() + 1, **fields
    )


@pytest.fixture
def lesson():
    return make_lesson()


def video_key(lesson, name="new"):
    return f"lessons/{lesson.pk}/{name}.mp4"


def slides_key(lesson, name="new"):
    return f"lessons/{lesson.pk}/{name}.pdf"


def upload_url(lesson_or_id):
    pk = getattr(lesson_or_id, "pk", lesson_or_id)
    return reverse("admin-lesson-uploads", kwargs={"pk": pk})


def request_upload(client, lesson_or_id, **body):
    return client.post(
        upload_url(lesson_or_id), body, content_type="application/json", headers=AUTH
    )


def lesson_url(lesson):
    return reverse("admin-lesson", kwargs={"pk": lesson.pk})


def patch_lesson(client, lesson, **body):
    return client.patch(lesson_url(lesson), body, content_type="application/json", headers=AUTH)


def delete(client, name, pk):
    return client.delete(reverse(name, kwargs={"pk": pk}), headers=AUTH)


def policy_conditions(upload):
    return json.loads(base64.b64decode(upload["fields"]["policy"]))["conditions"]


def expect_head(s3, key, exists=True):
    if exists:
        s3.add_response("head_object", {"ContentLength": 42}, {"Bucket": BUCKET, "Key": key})
    else:
        s3.add_client_error(
            "head_object",
            service_error_code="404",
            http_status_code=404,
            expected_params={"Bucket": BUCKET, "Key": key},
        )


def expect_delete(s3, key):
    s3.add_response("delete_object", {}, {"Bucket": BUCKET, "Key": key})


def presigned_get(url):
    """The key and expiry a presigned GET URL signs for, after checking its bucket."""
    parsed = urlparse(url)
    assert parsed.netloc == f"{BUCKET}.s3.us-east-2.amazonaws.com"
    query = parse_qs(parsed.query)
    assert "X-Amz-Signature" in query
    return parsed.path.lstrip("/"), int(query["X-Amz-Expires"][0])


class TestAccess:
    def test_rejects_requests_with_no_token(self, client, lesson):
        assert client.post(upload_url(lesson), {"kind": "video"}).status_code == 401

    def test_forbids_a_learner(self, client, learner, lesson, s3):
        assert request_upload(client, lesson, kind="video").status_code == 403
        assert patch_lesson(client, lesson, video_key=video_key(lesson)).status_code == 403
        lesson.refresh_from_db()
        assert lesson.video_key == ""


class TestRequestUpload:
    def test_a_video_is_an_mp4_of_up_to_2_gb(self, client, admin, lesson, s3):
        response = request_upload(client, lesson, kind="video")

        assert response.status_code == 200
        body = response.json()
        assert body["url"] == f"https://{BUCKET}.s3.us-east-2.amazonaws.com/"
        assert body["key"].startswith(f"lessons/{lesson.pk}/")
        assert body["key"].endswith(".mp4")
        assert body["fields"]["key"] == body["key"]
        assert body["fields"]["Content-Type"] == "video/mp4"
        conditions = policy_conditions(body)
        assert {"Content-Type": "video/mp4"} in conditions
        assert ["content-length-range", 1, 2 * 1024**3] in conditions

    def test_slides_are_a_pdf_of_up_to_100_mb(self, client, admin, lesson, s3):
        body = request_upload(client, lesson, kind="slides").json()

        assert body["key"].startswith(f"lessons/{lesson.pk}/")
        assert body["key"].endswith(".pdf")
        conditions = policy_conditions(body)
        assert {"Content-Type": "application/pdf"} in conditions
        assert ["content-length-range", 1, 100 * 1024**2] in conditions

    @pytest.mark.parametrize("kind", ["body", "thumbnail", ""])
    def test_refuses_other_kinds(self, client, admin, lesson, s3, kind):
        response = request_upload(client, lesson, kind=kind)

        assert response.status_code == 400
        assert "kind" in response.json()

    def test_requires_a_kind(self, client, admin, lesson, s3):
        assert request_upload(client, lesson).status_code == 400

    def test_every_upload_gets_a_new_key(self, client, admin, lesson, s3):
        first = request_upload(client, lesson, kind="video").json()
        second = request_upload(client, lesson, kind="video").json()

        assert first["key"] != second["key"]

    def test_leaves_the_lesson_unchanged(self, client, admin, lesson, s3):
        request_upload(client, lesson, kind="video")

        lesson.refresh_from_db()
        assert lesson.video_key == ""

    def test_an_unknown_lesson_is_not_found(self, client, admin, s3):
        assert request_upload(client, uuid.uuid4(), kind="video").status_code == 404


class TestRetrieve:
    def test_signs_urls_that_expire_after_an_hour(self, client, admin, lesson, s3):
        lesson.video_key = video_key(lesson)
        lesson.slides_key = slides_key(lesson)
        lesson.save()

        body = client.get(lesson_url(lesson), headers=AUTH).json()

        assert body["video_key"] == video_key(lesson)
        assert body["slides_key"] == slides_key(lesson)
        assert presigned_get(body["video_url"]) == (video_key(lesson), 3600)
        assert presigned_get(body["slides_url"]) == (slides_key(lesson), 3600)

    def test_no_file_is_a_blank_url(self, client, admin, lesson):
        body = client.get(lesson_url(lesson), headers=AUTH).json()

        assert body["video_url"] == ""
        assert body["slides_url"] == ""

    def test_public_endpoints_sign_nothing(self, client, s3):
        course = Course.objects.create(
            slug="foundations",
            title="Foundations",
            price_cents=12900,
            status=CourseStatus.PUBLISHED,
        )
        lesson = make_lesson(course)
        lesson.video_key = video_key(lesson)
        lesson.save()

        for response in (
            client.get(reverse("course-list")),
            client.get(reverse("course-detail", kwargs={"slug": "foundations"})),
        ):
            assert response.status_code == 200
            assert "X-Amz-Signature" not in response.content.decode()


class TestSave:
    @pytest.mark.parametrize(
        ("field", "key_for"), [("video_key", video_key), ("slides_key", slides_key)]
    )
    def test_saves_an_uploaded_key(self, client, admin, lesson, s3, field, key_for):
        key = key_for(lesson)
        expect_head(s3, key)

        response = patch_lesson(client, lesson, **{field: key})

        assert response.status_code == 200
        assert response.json()[field] == key
        assert response.json()["is_empty"] is False
        lesson.refresh_from_db()
        assert getattr(lesson, field) == key

    def test_returns_a_signed_url_for_the_new_file(self, client, admin, lesson, s3):
        expect_head(s3, video_key(lesson))

        body = patch_lesson(client, lesson, video_key=video_key(lesson)).json()

        assert presigned_get(body["video_url"])[0] == video_key(lesson)

    def test_saves_the_duration_with_the_video(self, client, admin, lesson, s3):
        expect_head(s3, video_key(lesson))

        patch_lesson(client, lesson, video_key=video_key(lesson), duration_seconds=754)

        lesson.refresh_from_db()
        assert lesson.duration_seconds == 754

    @pytest.mark.parametrize(
        ("field", "key"),
        [
            ("video_key", "lessons/elsewhere.mp4"),
            ("slides_key", "thumbnails/abc/new.pdf"),
            ("video_key", "new.mp4"),
        ],
    )
    def test_refuses_a_key_outside_the_lessons_prefix(self, client, admin, lesson, s3, field, key):
        response = patch_lesson(client, lesson, **{field: key})

        assert response.status_code == 400
        assert field in response.json()
        lesson.refresh_from_db()
        assert getattr(lesson, field) == ""

    def test_refuses_another_lessons_key(self, client, admin, lesson, s3):
        other = make_lesson(lesson.module.course, title="Wernicke")

        response = patch_lesson(client, lesson, video_key=video_key(other))

        assert response.status_code == 400
        assert "video_key" in response.json()

    def test_refuses_slides_as_the_video(self, client, admin, lesson, s3):
        response = patch_lesson(client, lesson, video_key=slides_key(lesson))

        assert response.status_code == 400
        assert response.json() == {"video_key": ["This isn't a video upload for this lesson."]}

    def test_refuses_a_video_as_the_slides(self, client, admin, lesson, s3):
        response = patch_lesson(client, lesson, slides_key=video_key(lesson))

        assert response.status_code == 400
        assert "slides_key" in response.json()

    def test_refuses_a_key_whose_object_doesnt_exist(self, client, admin, lesson, s3):
        expect_head(s3, video_key(lesson), exists=False)

        response = patch_lesson(client, lesson, video_key=video_key(lesson))

        assert response.status_code == 400
        assert response.json() == {
            "video_key": ["The upload didn't finish. Upload the file again."]
        }
        lesson.refresh_from_db()
        assert lesson.video_key == ""


class TestReplaceAndRemove:
    @pytest.mark.parametrize(
        ("field", "key_for"), [("video_key", video_key), ("slides_key", slides_key)]
    )
    def test_replacing_deletes_the_old_object_after_commit(
        self, client, admin, lesson, s3, django_capture_on_commit_callbacks, field, key_for
    ):
        old, new = key_for(lesson, "old"), key_for(lesson, "new")
        setattr(lesson, field, old)
        lesson.save()
        expect_head(s3, new)
        expect_delete(s3, old)

        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            assert patch_lesson(client, lesson, **{field: new}).status_code == 200

        assert len(callbacks) == 1
        lesson.refresh_from_db()
        assert getattr(lesson, field) == new

    @pytest.mark.parametrize(
        ("field", "key_for"), [("video_key", video_key), ("slides_key", slides_key)]
    )
    def test_removing_deletes_the_object(
        self, client, admin, lesson, s3, django_capture_on_commit_callbacks, field, key_for
    ):
        old = key_for(lesson, "old")
        setattr(lesson, field, old)
        lesson.save()
        expect_delete(s3, old)

        with django_capture_on_commit_callbacks(execute=True):
            response = patch_lesson(client, lesson, **{field: ""})

        assert response.status_code == 200
        assert response.json()[field.replace("_key", "_url")] == ""
        lesson.refresh_from_db()
        assert getattr(lesson, field) == ""

    def test_resending_the_same_key_neither_checks_nor_deletes(
        self, client, admin, lesson, s3, django_capture_on_commit_callbacks
    ):
        lesson.video_key = video_key(lesson)
        lesson.save()

        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            response = patch_lesson(client, lesson, video_key=video_key(lesson))

        assert response.status_code == 200
        assert callbacks == []

    def test_other_edits_leave_the_files_alone(
        self, client, admin, lesson, s3, django_capture_on_commit_callbacks
    ):
        lesson.video_key = video_key(lesson)
        lesson.slides_key = slides_key(lesson)
        lesson.save()

        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            assert patch_lesson(client, lesson, title="New").status_code == 200

        assert callbacks == []
        lesson.refresh_from_db()
        assert lesson.video_key == video_key(lesson)
        assert lesson.slides_key == slides_key(lesson)

    def test_a_failed_delete_still_saves(
        self, client, admin, lesson, s3, django_capture_on_commit_callbacks, caplog
    ):
        old = video_key(lesson, "old")
        lesson.video_key = old
        lesson.save()
        s3.add_client_error("delete_object", service_error_code="AccessDenied")

        with caplog.at_level(logging.ERROR, logger="common.storage"):
            with django_capture_on_commit_callbacks(execute=True):
                assert patch_lesson(client, lesson, video_key="").status_code == 200

        assert any(old in record.getMessage() for record in caplog.records)
        lesson.refresh_from_db()
        assert lesson.video_key == ""

    def test_a_refused_change_deletes_nothing(
        self, client, admin, lesson, s3, django_capture_on_commit_callbacks
    ):
        lesson.video_key = video_key(lesson, "old")
        lesson.save()

        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            response = patch_lesson(client, lesson, video_key="lessons/elsewhere.mp4")

        assert response.status_code == 400
        assert callbacks == []


class TestPublished:
    @pytest.fixture
    def published(self):
        """A published course that meets every publish rule, whose only lesson has a video."""
        course = Course.objects.create(
            slug="foundations",
            title="Foundations",
            description="About the course.",
            price_cents=12900,
            status=CourseStatus.PUBLISHED,
        )
        course.thumbnail_key = f"thumbnails/{course.pk}/cover.png"
        course.save()
        lesson = make_lesson(course)
        lesson.video_key = video_key(lesson, "old")
        lesson.save()
        return course

    def test_refuses_removing_a_lessons_only_part(
        self, client, admin, s3, published, django_capture_on_commit_callbacks
    ):
        lesson = Lesson.objects.get(module__course=published)

        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            response = patch_lesson(client, lesson, video_key="")

        assert response.status_code == 400
        assert response.json() == {"problems": ['Lesson "Broca" in "Anatomy" is empty.']}
        assert callbacks == []
        lesson.refresh_from_db()
        assert lesson.video_key == video_key(lesson, "old")

    def test_can_remove_a_part_when_another_remains(
        self, client, admin, s3, published, django_capture_on_commit_callbacks
    ):
        lesson = Lesson.objects.get(module__course=published)
        lesson.body = "Text."
        lesson.save()
        expect_delete(s3, video_key(lesson, "old"))

        with django_capture_on_commit_callbacks(execute=True):
            assert patch_lesson(client, lesson, video_key="").status_code == 200

    def test_can_replace_a_lessons_only_part(
        self, client, admin, s3, published, django_capture_on_commit_callbacks
    ):
        lesson = Lesson.objects.get(module__course=published)
        expect_head(s3, video_key(lesson, "new"))
        expect_delete(s3, video_key(lesson, "old"))

        with django_capture_on_commit_callbacks(execute=True):
            response = patch_lesson(client, lesson, video_key=video_key(lesson, "new"))

        assert response.status_code == 200


class TestDeleting:
    @pytest.fixture
    def course(self):
        """One module holding a lesson with both files and a lesson with only a body."""
        course = Course.objects.create(slug="foundations", title="Foundations", price_cents=100)
        both = make_lesson(course, title="Broca")
        both.video_key = video_key(both)
        both.slides_key = slides_key(both)
        both.save()
        make_lesson(course, title="Wernicke", body="Text.")
        return course

    def test_deleting_a_lesson_deletes_its_objects(
        self, client, admin, s3, course, django_capture_on_commit_callbacks
    ):
        lesson = Lesson.objects.get(title="Broca")
        expect_delete(s3, video_key(lesson))
        expect_delete(s3, slides_key(lesson))

        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            assert delete(client, "admin-lesson", lesson.pk).status_code == 204

        assert len(callbacks) == 2

    def test_deleting_a_lesson_without_files_touches_no_storage(
        self, client, admin, s3, course, django_capture_on_commit_callbacks
    ):
        lesson = Lesson.objects.get(title="Wernicke")

        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            assert delete(client, "admin-lesson", lesson.pk).status_code == 204

        assert callbacks == []

    def test_deleting_a_module_deletes_its_lessons_objects(
        self, client, admin, s3, course, django_capture_on_commit_callbacks
    ):
        lesson = Lesson.objects.get(title="Broca")
        expect_delete(s3, video_key(lesson))
        expect_delete(s3, slides_key(lesson))

        with django_capture_on_commit_callbacks(execute=True):
            response = delete(client, "admin-module", course.modules.get().pk)

        assert response.status_code == 204
        assert not Lesson.objects.exists()

    def test_deleting_a_course_deletes_its_lessons_objects(
        self, client, admin, s3, course, django_capture_on_commit_callbacks
    ):
        lesson = Lesson.objects.get(title="Broca")
        expect_delete(s3, video_key(lesson))
        expect_delete(s3, slides_key(lesson))

        with django_capture_on_commit_callbacks(execute=True):
            response = delete(client, "admin-course-detail", course.pk)

        assert response.status_code == 204
        assert not Course.objects.exists()

    def test_a_failed_delete_is_logged_not_raised(
        self, client, admin, s3, course, django_capture_on_commit_callbacks, caplog
    ):
        lesson = Lesson.objects.get(title="Broca")
        s3.add_client_error("delete_object", service_error_code="AccessDenied")
        expect_delete(s3, slides_key(lesson))

        with caplog.at_level(logging.ERROR, logger="common.storage"):
            with django_capture_on_commit_callbacks(execute=True):
                assert delete(client, "admin-lesson", lesson.pk).status_code == 204

        (record,) = caplog.records
        assert video_key(lesson) in record.getMessage()
        assert not Lesson.objects.filter(pk=lesson.pk).exists()

    def test_a_refused_delete_touches_no_storage(
        self, client, admin, s3, course, django_capture_on_commit_callbacks
    ):
        course.status = CourseStatus.PUBLISHED
        course.save()
        module = course.modules.get()

        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            assert delete(client, "admin-module", module.pk).status_code == 400

        assert callbacks == []
        assert Lesson.objects.filter(title="Broca").exists()
