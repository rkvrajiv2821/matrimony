"""Private S3-compatible object storage. Objects are never publicly readable.

boto3 is synchronous, so every call runs in a worker thread.
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import anyio
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.common.config import get_settings


@dataclass(frozen=True)
class PresignedPost:
    url: str
    fields: dict[str, str]


@lru_cache
def _client() -> Any:
    s = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=s.storage_endpoint_url,
        region_name=s.storage_region,
        aws_access_key_id=s.storage_access_key.get_secret_value(),
        aws_secret_access_key=s.storage_secret_key.get_secret_value(),
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def _bucket() -> str:
    return get_settings().storage_bucket


async def ensure_bucket() -> None:
    def run() -> None:
        try:
            _client().head_bucket(Bucket=_bucket())
        except ClientError:
            _client().create_bucket(
                Bucket=_bucket(),
                CreateBucketConfiguration={"LocationConstraint": get_settings().storage_region},
            )

    await anyio.to_thread.run_sync(run)


async def presign_post(key: str, content_type: str, max_bytes: int, ttl: int) -> PresignedPost:
    def run() -> dict[str, Any]:
        return dict(
            _client().generate_presigned_post(
                Bucket=_bucket(),
                Key=key,
                Fields={"Content-Type": content_type},
                Conditions=[
                    {"Content-Type": content_type},
                    ["content-length-range", 1, max_bytes],
                ],
                ExpiresIn=ttl,
            )
        )

    result = await anyio.to_thread.run_sync(run)
    return PresignedPost(url=result["url"], fields=dict(result["fields"]))


async def size_of(key: str) -> int | None:
    def run() -> int | None:
        try:
            return int(_client().head_object(Bucket=_bucket(), Key=key)["ContentLength"])
        except ClientError:
            return None

    return await anyio.to_thread.run_sync(run)


async def get_bytes(key: str) -> bytes | None:
    def run() -> bytes | None:
        try:
            body = _client().get_object(Bucket=_bucket(), Key=key)["Body"]
            return bytes(body.read())
        except ClientError:
            return None

    return await anyio.to_thread.run_sync(run)


async def put_bytes(key: str, data: bytes, content_type: str) -> None:
    def run() -> None:
        _client().put_object(
            Bucket=_bucket(),
            Key=key,
            Body=data,
            ContentType=content_type,
            ServerSideEncryption="AES256",
        )

    await anyio.to_thread.run_sync(run)


async def delete(*keys: str) -> None:
    if not keys:
        return

    def run() -> None:
        _client().delete_objects(
            Bucket=_bucket(), Delete={"Objects": [{"Key": k} for k in keys], "Quiet": True}
        )

    await anyio.to_thread.run_sync(run)
