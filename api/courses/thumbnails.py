"""Course thumbnails, in the thumbnail bucket under ``thumbnails/<course id>/``."""

import uuid

from django.conf import settings
from django.db import transaction

from common import storage

# Content type → file extension.
TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
MAX_BYTES = 5 * 1024 * 1024


def key_prefix(course):
    return f"thumbnails/{course.pk}/"


def presign_upload(course, content_type):
    """A presigned POST for a new key, with that ``key`` added.

    ``content_type`` must be one of ``TYPES``. Every upload gets a fresh key, so a
    replaced thumbnail is never served from a stale CloudFront cache.
    """
    key = f"{key_prefix(course)}{uuid.uuid4().hex}.{TYPES[content_type]}"
    upload = storage.presign_upload(
        settings.AWS_THUMBNAIL_BUCKET_NAME, key, content_type, MAX_BYTES
    )
    return {**upload, "key": key}


def exists(key):
    return storage.head(settings.AWS_THUMBNAIL_BUCKET_NAME, key) is not None


def delete_after_commit(key):
    """Deletes the object once the current transaction commits, or now outside one."""
    transaction.on_commit(lambda: storage.delete(settings.AWS_THUMBNAIL_BUCKET_NAME, key))
