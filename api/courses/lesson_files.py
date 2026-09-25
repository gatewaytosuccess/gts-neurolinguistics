"""Lesson video and slides, in the private bucket under ``lessons/<lesson id>/``."""

import uuid
from dataclasses import dataclass

from django.conf import settings
from django.db import transaction

from common import storage


@dataclass(frozen=True)
class FileKind:
    field: str
    content_type: str
    extension: str
    max_bytes: int


KINDS = {
    "video": FileKind("video_key", "video/mp4", "mp4", 2 * 1024**3),
    "slides": FileKind("slides_key", "application/pdf", "pdf", 100 * 1024**2),
}
DOWNLOAD_EXPIRES_SECONDS = 60 * 60


def key_prefix(lesson):
    return f"lessons/{lesson.pk}/"


def is_upload_for(lesson, kind, key):
    """Whether ``key`` is one ``presign_upload`` could have made for this lesson and kind."""
    return key.startswith(key_prefix(lesson)) and key.endswith(f".{KINDS[kind].extension}")


def presign_upload(lesson, kind):
    """A presigned POST for a new key, with that ``key`` added. ``kind`` is a ``KINDS`` key."""
    file_kind = KINDS[kind]
    key = f"{key_prefix(lesson)}{uuid.uuid4().hex}.{file_kind.extension}"
    upload = storage.presign_upload(
        settings.AWS_PRIVATE_BUCKET_NAME, key, file_kind.content_type, file_kind.max_bytes
    )
    return {**upload, "key": key}


def exists(key):
    return storage.head(settings.AWS_PRIVATE_BUCKET_NAME, key) is not None


def download_url(key):
    """A presigned GET URL that expires after an hour; blank for a blank key.

    Admin responses only: whoever holds the URL can read the file.
    """
    if not key:
        return ""
    return storage.presign_download(settings.AWS_PRIVATE_BUCKET_NAME, key, DOWNLOAD_EXPIRES_SECONDS)


def keys_of(lessons):
    """The non-blank video and slides keys of a ``Lesson`` queryset."""
    return [key for pair in lessons.values_list("video_key", "slides_key") for key in pair if key]


def delete_after_commit(*keys):
    """Deletes the objects once the current transaction commits, or now outside one."""
    for key in keys:
        transaction.on_commit(lambda key=key: storage.delete(settings.AWS_PRIVATE_BUCKET_NAME, key))
