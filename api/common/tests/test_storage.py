import base64
import json
import logging
from urllib.parse import parse_qs, urlparse

import pytest
from botocore.exceptions import ClientError

from common import storage


def policy_conditions(upload):
    return json.loads(base64.b64decode(upload["fields"]["policy"]))["conditions"]


class TestPresignUpload:
    def test_posts_to_the_buckets_regional_endpoint(self, s3):
        upload = storage.presign_upload("gts-thumbnails", "thumbnails/a/b.png", "image/png", 100)

        assert upload["url"] == "https://gts-thumbnails.s3.us-east-2.amazonaws.com/"

    def test_the_fields_name_the_key_and_content_type(self, s3):
        upload = storage.presign_upload("gts-thumbnails", "thumbnails/a/b.png", "image/png", 100)

        assert upload["fields"]["key"] == "thumbnails/a/b.png"
        assert upload["fields"]["Content-Type"] == "image/png"

    def test_the_policy_pins_the_bucket_key_and_content_type(self, s3):
        upload = storage.presign_upload("gts-thumbnails", "thumbnails/a/b.png", "image/png", 100)

        conditions = policy_conditions(upload)
        assert {"bucket": "gts-thumbnails"} in conditions
        assert {"key": "thumbnails/a/b.png"} in conditions
        assert {"Content-Type": "image/png"} in conditions

    def test_the_policy_limits_the_size(self, s3):
        upload = storage.presign_upload("gts-thumbnails", "thumbnails/a/b.png", "image/png", 100)

        assert ["content-length-range", 1, 100] in policy_conditions(upload)


class TestPresignDownload:
    def test_signs_a_get_for_the_object(self, s3):
        url = urlparse(storage.presign_download("gts-private", "lessons/a/b c.mp4", 3600))

        assert url.netloc == "gts-private.s3.us-east-2.amazonaws.com"
        assert url.path == "/lessons/a/b%20c.mp4"
        query = parse_qs(url.query)
        assert query["X-Amz-Expires"] == ["3600"]
        assert "X-Amz-Signature" in query


class TestHead:
    def test_returns_the_objects_metadata(self, s3):
        s3.add_response(
            "head_object",
            {"ContentLength": 42, "ContentType": "image/png"},
            {"Bucket": "gts-thumbnails", "Key": "thumbnails/a/b.png"},
        )

        metadata = storage.head("gts-thumbnails", "thumbnails/a/b.png")

        assert metadata["ContentLength"] == 42
        assert metadata["ContentType"] == "image/png"

    def test_a_missing_object_is_none(self, s3):
        s3.add_client_error("head_object", service_error_code="404", http_status_code=404)

        assert storage.head("gts-thumbnails", "thumbnails/a/b.png") is None

    def test_other_failures_raise(self, s3):
        s3.add_client_error("head_object", service_error_code="403", http_status_code=403)

        with pytest.raises(ClientError):
            storage.head("gts-thumbnails", "thumbnails/a/b.png")


class TestDelete:
    def test_deletes_the_object(self, s3):
        s3.add_response(
            "delete_object", {}, {"Bucket": "gts-thumbnails", "Key": "thumbnails/a/b.png"}
        )

        storage.delete("gts-thumbnails", "thumbnails/a/b.png")

    def test_a_failure_is_logged_not_raised(self, s3, caplog):
        s3.add_client_error("delete_object", service_error_code="AccessDenied")

        with caplog.at_level(logging.ERROR, logger="common.storage"):
            storage.delete("gts-thumbnails", "thumbnails/a/b.png")

        (record,) = caplog.records
        assert "s3://gts-thumbnails/thumbnails/a/b.png" in record.getMessage()
        assert record.exc_info is not None


class TestPublicUrl:
    def test_builds_the_cloudfront_url(self, settings):
        settings.CLOUDFRONT_DOMAIN = "cdn.example.com"

        assert (
            storage.public_url("thumbnails/a/b.png") == "https://cdn.example.com/thumbnails/a/b.png"
        )

    def test_escapes_the_key(self, settings):
        settings.CLOUDFRONT_DOMAIN = "cdn.example.com"

        assert storage.public_url("thumbnails/a/b c#.png") == (
            "https://cdn.example.com/thumbnails/a/b%20c%23.png"
        )

    def test_a_blank_key_is_blank(self, settings):
        settings.CLOUDFRONT_DOMAIN = "cdn.example.com"

        assert storage.public_url("") == ""
