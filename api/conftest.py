import pytest
from botocore.stub import Stubber

from common import storage


@pytest.fixture
def s3(settings):
    """A ``Stubber`` on the storage module's client, with fake credentials.

    Any S3 call a test hasn't queued a response for fails the test.
    """
    settings.AWS_S3_REGION_NAME = "us-east-2"
    settings.AWS_ACCESS_KEY_ID = "AKIAEXAMPLE"
    settings.AWS_SECRET_ACCESS_KEY = "secret"
    settings.AWS_PRIVATE_BUCKET_NAME = "gts-private"
    settings.AWS_THUMBNAIL_BUCKET_NAME = "gts-thumbnails"
    settings.CLOUDFRONT_DOMAIN = "cdn.example.com"
    storage._client.cache_clear()
    with Stubber(storage._client()) as stubber:
        yield stubber
        stubber.assert_no_pending_responses()
    storage._client.cache_clear()
