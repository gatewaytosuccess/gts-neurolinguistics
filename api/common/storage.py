"""The only code that talks to S3. Callers pass bucket names from settings and
store object keys, never URLs."""

import functools
import logging
from urllib.parse import quote

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings

logger = logging.getLogger(__name__)

UPLOAD_EXPIRES_SECONDS = 15 * 60


@functools.cache
def _client():
    return boto3.client(
        "s3",
        region_name=settings.AWS_S3_REGION_NAME or None,
        # Blank falls back to boto3's own chain (an instance role in production).
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
        # The regional endpoint: the global one redirects for a new bucket, and a
        # redirected browser POST fails CORS.
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "virtual", "us_east_1_regional_endpoint": "regional"},
        ),
    )


def presign_upload(bucket, key, content_type, max_bytes):
    """A presigned POST for one object: ``{"url": ..., "fields": {...}}``.

    The browser sends ``fields`` then the file as multipart form data. S3 refuses
    any other key, a different ``Content-Type``, an empty file, or one over
    ``max_bytes``.
    """
    return _client().generate_presigned_post(
        Bucket=bucket,
        Key=key,
        Fields={"Content-Type": content_type},
        Conditions=[
            {"Content-Type": content_type},
            ["content-length-range", 1, max_bytes],
        ],
        ExpiresIn=UPLOAD_EXPIRES_SECONDS,
    )


def presign_download(bucket, key, expires):
    """A presigned GET URL for one object, valid for ``expires`` seconds.

    Anyone holding the URL can read the object until it expires.
    """
    return _client().generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expires
    )


def head(bucket, key):
    """The object's metadata, or ``None`` if it doesn't exist. Other failures raise."""
    try:
        return _client().head_object(Bucket=bucket, Key=key)
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") in {"404", "NoSuchKey"}:
            return None
        raise


def delete(bucket, key):
    """Best effort: a failure is logged, never raised, and leaves an orphan."""
    try:
        _client().delete_object(Bucket=bucket, Key=key)
    except (BotoCoreError, ClientError):
        logger.exception("Could not delete s3://%s/%s", bucket, key)


def public_url(key):
    """The key's CloudFront URL; blank for a blank key."""
    if not key:
        return ""
    return f"https://{settings.CLOUDFRONT_DOMAIN}/{quote(key)}"
