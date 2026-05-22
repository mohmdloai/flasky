"""
S3 / MinIO storage helpers.

Two endpoints are kept distinct on purpose:
  - MINIO_ENDPOINT        — backend → MinIO (container-internal, e.g. http://minio:9000)
  - MINIO_PUBLIC_ENDPOINT — browser-facing URLs (e.g. http://localhost:9000 or a CDN)
"""
import uuid
from typing import BinaryIO, Optional

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError
from flask import current_app


_client = None


def get_client():
    global _client
    if _client is None:
        cfg = current_app.config
        _client = boto3.client(
            's3',
            endpoint_url=cfg['MINIO_ENDPOINT'],
            aws_access_key_id=cfg['MINIO_ACCESS_KEY'],
            aws_secret_access_key=cfg['MINIO_SECRET_KEY'],
            region_name=cfg['MINIO_REGION'],
            config=BotoConfig(signature_version='s3v4'),
        )
    return _client


def generate_object_key(prefix: str, filename: str) -> str:
    """e.g. products/9f2c.../photo.jpg — uuid avoids collisions and makes keys unguessable."""
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'bin'
    return f"{prefix}/{uuid.uuid4().hex}.{ext}"


def upload_fileobj(
    bucket: str,
    key: str,
    fileobj: BinaryIO,
    content_type: Optional[str] = None,
) -> str:
    extra = {'ContentType': content_type} if content_type else {}
    get_client().upload_fileobj(fileobj, bucket, key, ExtraArgs=extra)
    return key


def delete_object(bucket: str, key: str) -> None:
    try:
        get_client().delete_object(Bucket=bucket, Key=key)
    except ClientError:
        # Idempotent delete — missing object is not an error from our perspective.
        pass


def build_public_url(bucket: str, key: str) -> str:
    base = current_app.config['MINIO_PUBLIC_ENDPOINT'].rstrip('/')
    return f"{base}/{bucket}/{key}"


def generate_presigned_put(bucket: str, key: str, expires_in: int = 600) -> str:
    """Signed URL for direct browser-to-MinIO PUT uploads (avoids proxying through Flask)."""
    return get_client().generate_presigned_url(
        'put_object',
        Params={'Bucket': bucket, 'Key': key},
        ExpiresIn=expires_in,
    )
