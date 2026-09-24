import base64
import json
import logging
import uuid

import pytest
from django.urls import reverse

from courses.models import Course, CourseStatus
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


@pytest.fixture
def course():
    return make_course("foundations")


def make_course(slug, status=CourseStatus.DRAFT, **fields):
    fields.setdefault("title", slug.replace("-", " ").title())
    fields.setdefault("description", "About the course.")
    fields.setdefault("price_cents", 12900)
    return Course.objects.create(slug=slug, status=status, **fields)


def key_for(course, name="new.png"):
    return f"thumbnails/{course.pk}/{name}"


def upload_url(course_or_id):
    pk = getattr(course_or_id, "pk", course_or_id)
    return reverse("admin-course-thumbnail-upload", kwargs={"pk": pk})


def request_upload(client, course_or_id, **body):
    return client.post(
        upload_url(course_or_id), body, content_type="application/json", headers=AUTH
    )


def patch_course(client, course, **body):
    return client.patch(
        reverse("admin-course-detail", kwargs={"pk": course.pk}),
        body,
        content_type="application/json",
        headers=AUTH,
    )


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


class TestAccess:
    def test_rejects_requests_with_no_token(self, client, course):
        assert client.post(upload_url(course), {"content_type": "image/png"}).status_code == 401

    def test_forbids_a_learner(self, client, learner, course, s3):
        assert request_upload(client, course, content_type="image/png").status_code == 403
        assert patch_course(client, course, thumbnail_key=key_for(course)).status_code == 403
        course.refresh_from_db()
        assert course.thumbnail_key == ""


class TestRequestUpload:
    def test_returns_a_presigned_post_for_a_key_under_the_course(self, client, admin, course, s3):
        response = request_upload(client, course, content_type="image/png")

        assert response.status_code == 200
        body = response.json()
        assert body["url"] == f"https://{BUCKET}.s3.us-east-2.amazonaws.com/"
        assert body["key"].startswith(f"thumbnails/{course.pk}/")
        assert body["key"].endswith(".png")
        assert body["fields"]["key"] == body["key"]
        assert body["fields"]["Content-Type"] == "image/png"

    def test_the_policy_allows_up_to_5_mb(self, client, admin, course, s3):
        body = request_upload(client, course, content_type="image/webp").json()

        conditions = json.loads(base64.b64decode(body["fields"]["policy"]))["conditions"]
        assert ["content-length-range", 1, 5 * 1024 * 1024] in conditions
        assert {"Content-Type": "image/webp"} in conditions

    @pytest.mark.parametrize(
        ("content_type", "extension"),
        [("image/jpeg", ".jpg"), ("image/png", ".png"), ("image/webp", ".webp")],
    )
    def test_accepts_jpeg_png_and_webp(self, client, admin, course, s3, content_type, extension):
        body = request_upload(client, course, content_type=content_type).json()

        assert body["key"].endswith(extension)

    @pytest.mark.parametrize("content_type", ["image/gif", "image/svg+xml", "application/pdf"])
    def test_refuses_other_types(self, client, admin, course, s3, content_type):
        response = request_upload(client, course, content_type=content_type)

        assert response.status_code == 400
        assert response.json()["content_type"] == ["Choose a JPEG, PNG or WebP image."]

    def test_requires_a_content_type(self, client, admin, course, s3):
        assert request_upload(client, course).status_code == 400

    def test_every_upload_gets_a_new_key(self, client, admin, course, s3):
        first = request_upload(client, course, content_type="image/png").json()
        second = request_upload(client, course, content_type="image/png").json()

        assert first["key"] != second["key"]

    def test_leaves_the_course_unchanged(self, client, admin, course, s3):
        request_upload(client, course, content_type="image/png")

        course.refresh_from_db()
        assert course.thumbnail_key == ""

    def test_an_unknown_course_is_not_found(self, client, admin, s3):
        assert request_upload(client, uuid.uuid4(), content_type="image/png").status_code == 404


class TestSave:
    def test_saves_an_uploaded_key(self, client, admin, course, s3):
        key = key_for(course)
        expect_head(s3, key)

        response = patch_course(client, course, thumbnail_key=key)

        assert response.status_code == 200
        assert response.json()["thumbnail_key"] == key
        assert response.json()["thumbnail_url"] == f"https://cdn.example.com/{key}"
        course.refresh_from_db()
        assert course.thumbnail_key == key

    def test_refuses_a_key_outside_the_courses_prefix(self, client, admin, course, s3):
        response = patch_course(client, course, thumbnail_key="thumbnails/elsewhere.png")

        assert response.status_code == 400
        assert "thumbnail_key" in response.json()
        course.refresh_from_db()
        assert course.thumbnail_key == ""

    def test_refuses_another_courses_key(self, client, admin, course, s3):
        other = make_course("other")

        response = patch_course(client, course, thumbnail_key=key_for(other))

        assert response.status_code == 400
        assert "thumbnail_key" in response.json()

    def test_refuses_a_key_whose_object_doesnt_exist(self, client, admin, course, s3):
        key = key_for(course)
        expect_head(s3, key, exists=False)

        response = patch_course(client, course, thumbnail_key=key)

        assert response.status_code == 400
        assert "thumbnail_key" in response.json()
        course.refresh_from_db()
        assert course.thumbnail_key == ""

    def test_cant_be_set_on_create(self, client, admin, s3):
        response = client.post(
            reverse("admin-course-list"),
            {"title": "New", "price_cents": 100, "thumbnail_key": "thumbnails/x/y.png"},
            content_type="application/json",
            headers=AUTH,
        )

        assert response.status_code == 400
        assert "thumbnail_key" in response.json()
        assert not Course.objects.exists()


class TestReplaceAndRemove:
    def test_replacing_deletes_the_old_object_after_commit(
        self, client, admin, course, s3, django_capture_on_commit_callbacks
    ):
        old, new = key_for(course, "old.png"), key_for(course, "new.png")
        course.thumbnail_key = old
        course.save()
        expect_head(s3, new)
        expect_delete(s3, old)

        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            assert patch_course(client, course, thumbnail_key=new).status_code == 200

        assert len(callbacks) == 1
        course.refresh_from_db()
        assert course.thumbnail_key == new

    def test_removing_deletes_the_object(
        self, client, admin, course, s3, django_capture_on_commit_callbacks
    ):
        old = key_for(course, "old.png")
        course.thumbnail_key = old
        course.save()
        expect_delete(s3, old)

        with django_capture_on_commit_callbacks(execute=True):
            response = patch_course(client, course, thumbnail_key="")

        assert response.status_code == 200
        assert response.json()["thumbnail_url"] == ""
        course.refresh_from_db()
        assert course.thumbnail_key == ""

    def test_resending_the_same_key_neither_checks_nor_deletes(
        self, client, admin, course, s3, django_capture_on_commit_callbacks
    ):
        key = key_for(course)
        course.thumbnail_key = key
        course.save()

        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            assert patch_course(client, course, thumbnail_key=key).status_code == 200

        assert callbacks == []

    def test_other_edits_leave_the_thumbnail_alone(
        self, client, admin, course, s3, django_capture_on_commit_callbacks
    ):
        course.thumbnail_key = key_for(course)
        course.save()

        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            assert patch_course(client, course, title="New Title").status_code == 200

        assert callbacks == []
        course.refresh_from_db()
        assert course.thumbnail_key == key_for(course)

    def test_a_failed_delete_still_saves(
        self, client, admin, course, s3, django_capture_on_commit_callbacks, caplog
    ):
        old, new = key_for(course, "old.png"), key_for(course, "new.png")
        course.thumbnail_key = old
        course.save()
        expect_head(s3, new)
        s3.add_client_error("delete_object", service_error_code="AccessDenied")

        with caplog.at_level(logging.ERROR, logger="common.storage"):
            with django_capture_on_commit_callbacks(execute=True):
                assert patch_course(client, course, thumbnail_key=new).status_code == 200

        assert any(old in record.getMessage() for record in caplog.records)
        course.refresh_from_db()
        assert course.thumbnail_key == new

    def test_a_refused_change_deletes_nothing(
        self, client, admin, course, s3, django_capture_on_commit_callbacks
    ):
        course.thumbnail_key = key_for(course, "old.png")
        course.save()

        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            response = patch_course(client, course, thumbnail_key="thumbnails/elsewhere.png")

        assert response.status_code == 400
        assert callbacks == []


class TestPublished:
    def test_refuses_removing_it(self, client, admin, s3, django_capture_on_commit_callbacks):
        course = make_course("foundations", status=CourseStatus.PUBLISHED)
        course.thumbnail_key = key_for(course)
        course.save()

        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            response = patch_course(client, course, thumbnail_key="")

        assert response.status_code == 400
        assert response.json()["thumbnail_key"] == ["A published course needs a thumbnail."]
        assert callbacks == []
        course.refresh_from_db()
        assert course.thumbnail_key == key_for(course)

    def test_can_replace_it(self, client, admin, s3, django_capture_on_commit_callbacks):
        course = make_course("foundations", status=CourseStatus.PUBLISHED)
        old, new = key_for(course, "old.png"), key_for(course, "new.png")
        course.thumbnail_key = old
        course.save()
        expect_head(s3, new)
        expect_delete(s3, old)

        with django_capture_on_commit_callbacks(execute=True):
            assert patch_course(client, course, thumbnail_key=new).status_code == 200
