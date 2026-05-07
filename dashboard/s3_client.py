"""S3 file retrieval for the dashboard proxy."""

from __future__ import annotations

import logging
from urllib.parse import urlparse

import boto3
from botocore.config import Config as BotoConfig

import config

logger = logging.getLogger(__name__)

_s3 = None


def _get_s3():
    """Lazy-initialize and return the boto3 S3 client."""
    global _s3
    if _s3 is not None:
        return _s3

    if not config.AWS_BUCKET_NAME:
        logger.warning("[s3] AWS_BUCKET_NAME not configured, S3 proxy disabled")
        return None

    kwargs: dict = {
        "service_name": "s3",
        "config": BotoConfig(signature_version="s3v4"),
    }

    if config.AWS_REGION:
        kwargs["region_name"] = config.AWS_REGION
    if config.AWS_ACCESS_KEY_ID and config.AWS_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = config.AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = config.AWS_SECRET_ACCESS_KEY
    if config.AWS_ENDPOINT_URL:
        kwargs["endpoint_url"] = config.AWS_ENDPOINT_URL

    _s3 = boto3.client(**kwargs)
    logger.info("[s3] boto3 client initialized")
    return _s3


def extract_key_from_url(file_url_or_key: str) -> str:
    """Extract the S3 object key from a presigned URL or return the key as-is.

    Mirrors the TypeScript extractKeyFromS3Url logic from @librechat/api.
    """
    if not file_url_or_key:
        return ""

    # Already a plain key (no scheme)
    if not file_url_or_key.startswith(("http://", "https://")):
        return file_url_or_key.lstrip("/")

    try:
        parsed = urlparse(file_url_or_key)
        hostname = parsed.hostname or ""
        pathname = parsed.path.lstrip("/")

        # Custom endpoint with path-style
        if config.AWS_ENDPOINT_URL and config.AWS_FORCE_PATH_STYLE:
            endpoint_path = urlparse(config.AWS_ENDPOINT_URL).path.strip("/")
            bucket = config.AWS_BUCKET_NAME
            prefix = f"{endpoint_path}/{bucket}" if endpoint_path else bucket
            if pathname.startswith(prefix):
                key = pathname[len(prefix) :].lstrip("/")
                return key

        # Standard S3 virtual-hosted-style
        if (
            hostname == "s3.amazonaws.com"
            or hostname.startswith("s3.")
            or hostname.endswith(".s3.amazonaws.com")
            or (config.AWS_BUCKET_NAME and pathname.startswith(config.AWS_BUCKET_NAME + "/"))
        ):
            first_slash = pathname.find("/")
            if first_slash > 0:
                return pathname[first_slash + 1 :]

        # Path is the key directly
        return pathname
    except Exception:
        # Not a URL — treat as key
        return file_url_or_key.lstrip("/")


def get_object_bytes(file_url_or_key: str) -> tuple[bytes, str]:
    """Fetch an object from S3. Returns (body_bytes, content_type)."""
    s3 = _get_s3()
    if not s3:
        raise RuntimeError("S3 client not configured")

    key = extract_key_from_url(file_url_or_key)
    if not key:
        raise ValueError(f"Cannot extract S3 key from: {file_url_or_key}")

    resp = s3.get_object(Bucket=config.AWS_BUCKET_NAME, Key=key)
    body = resp["Body"].read()
    content_type = resp.get("ContentType", "application/octet-stream")
    return body, content_type


def get_object_stream(file_url_or_key: str):
    """Fetch an object from S3 as a streaming body. Returns (StreamingBody, content_type, content_length)."""
    s3 = _get_s3()
    if not s3:
        raise RuntimeError("S3 client not configured")

    key = extract_key_from_url(file_url_or_key)
    if not key:
        raise ValueError(f"Cannot extract S3 key from: {file_url_or_key}")

    resp = s3.get_object(Bucket=config.AWS_BUCKET_NAME, Key=key)
    return resp["Body"], resp.get("ContentType", "application/octet-stream"), resp.get("ContentLength", 0)
