"""S3 presigned URL helper for file preview and download."""

import os
import logging
from urllib.parse import urlparse
from functools import lru_cache

import boto3

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_s3_client():
    """Create an S3 client from environment variables."""
    region = os.getenv("AWS_REGION", "")
    endpoint_url = os.getenv("AWS_ENDPOINT_URL")
    return boto3.client(
        "s3",
        region_name=region,
        endpoint_url=endpoint_url,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )


def _get_bucket() -> str:
    return os.getenv("AWS_BUCKET_NAME", "")


def _parse_s3_key(filepath: str) -> str | None:
    """Extract the S3 object key from a stored filepath (presigned URL or direct URL).

    URL format: https://{endpoint}/{bucket}/{basePath}/{userId}/{fileName}
    Key format: {basePath}/{userId}/{fileName}
    """
    if not filepath:
        return None

    bucket = _get_bucket()
    if not bucket:
        return None

    parsed = urlparse(filepath)
    path = parsed.path.lstrip("/")

    # Path-style: /{bucket}/{key}
    if path.startswith(bucket + "/"):
        return path[len(bucket) + 1:]

    # Virtual-hosted-style: key is the entire path
    if path:
        return path

    return None


def get_presigned_url(filepath: str, expires: int = 3600, download: bool = False, filename: str = "") -> str | None:
    """Generate a fresh presigned URL for an S3 object.

    Args:
        filepath: The stored filepath (presigned URL) from MongoDB.
        expires: URL expiry in seconds (default 1 hour).
        download: If True, set Content-Disposition for download.
        filename: Custom filename for download.

    Returns:
        Presigned URL string, or None if not an S3 file.
    """
    key = _parse_s3_key(filepath)
    if not key:
        return None

    bucket = _get_bucket()
    try:
        client = _get_s3_client()
        params = {"Bucket": bucket, "Key": key}
        if download and filename:
            safe = filename.replace('"', "").replace("\r", "").replace("\n", "")
            params["ResponseContentDisposition"] = f'attachment; filename="{safe}"'

        return client.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=expires,
        )
    except Exception:
        logger.exception("Failed to generate presigned URL for key=%s", key)
        return None
