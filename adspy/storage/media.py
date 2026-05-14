"""MediaStore — uploads/downloads media. Cloudflare R2 if configured, else local filesystem.

R2 has zero egress; local is the no-config dev path.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Protocol

from adspy.config import Settings, get_settings
from adspy.utils.logging import get_logger

log = get_logger(__name__)


class MediaStore(Protocol):
    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Write the blob and return a stable URL/path."""

    def url_for(self, key: str) -> str:
        """Return a fetchable URL (presigned for R2, file:// for local)."""

    def exists(self, key: str) -> bool: ...


class LocalFsStore:
    def __init__(self, root: str = "local-cache/media") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return self.url_for(key)

    def url_for(self, key: str) -> str:
        return (self.root / key).resolve().as_uri()

    def exists(self, key: str) -> bool:
        return (self.root / key).exists()


class R2Store:
    """Cloudflare R2 (S3-compatible). Uses boto3 — no dependency on the heavier aiobotocore."""

    def __init__(self, settings: Settings) -> None:
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("boto3 is not installed (poetry install)") from exc

        endpoint = settings.r2_endpoint or (
            f"https://{settings.r2_account_id}.r2.cloudflarestorage.com"
        )
        self._bucket = settings.r2_bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=settings.r2_access_key_id.get_secret_value(),
            aws_secret_access_key=settings.r2_secret_access_key.get_secret_value(),
            region_name="auto",
        )

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        self._client.put_object(
            Bucket=self._bucket, Key=key, Body=data, ContentType=content_type
        )
        return self.url_for(key)

    def url_for(self, key: str) -> str:
        return self._client.generate_presigned_url(
            "get_object", Params={"Bucket": self._bucket, "Key": key}, ExpiresIn=3600
        )

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except ClientError:
            return False


@lru_cache(maxsize=1)
def get_media_store() -> MediaStore:
    s = get_settings()
    if s.r2_account_id and s.r2_access_key_id.get_secret_value():
        try:
            return R2Store(s)
        except Exception as exc:  # noqa: BLE001
            log.warning("r2_init_failed_falling_back_local", error=str(exc))
    return LocalFsStore()
