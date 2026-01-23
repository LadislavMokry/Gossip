from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import boto3
from botocore.config import Config

from app.config import get_settings


@dataclass
class R2Config:
    access_key_id: str
    secret_access_key: str
    bucket: str
    endpoint: str
    public_base_url: str


def _load_config() -> R2Config:
    settings = get_settings()
    missing = []
    if not settings.r2_access_key_id:
        missing.append("R2_ACCESS_KEY_ID")
    if not settings.r2_secret_access_key:
        missing.append("R2_SECRET_ACCESS_KEY")
    if not settings.r2_bucket:
        missing.append("R2_BUCKET")
    if not settings.r2_endpoint:
        missing.append("R2_ENDPOINT")
    if not settings.r2_public_base_url:
        missing.append("R2_PUBLIC_BASE_URL")
    if missing:
        raise RuntimeError(f"Missing R2 config: {', '.join(missing)}")
    return R2Config(
        access_key_id=settings.r2_access_key_id,
        secret_access_key=settings.r2_secret_access_key,
        bucket=settings.r2_bucket,
        endpoint=settings.r2_endpoint.rstrip("/"),
        public_base_url=settings.r2_public_base_url.rstrip("/"),
    )


def _client(config: R2Config):
    return boto3.client(
        "s3",
        endpoint_url=config.endpoint,
        aws_access_key_id=config.access_key_id,
        aws_secret_access_key=config.secret_access_key,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def public_url(key: str) -> str:
    cfg = _load_config()
    key = key.lstrip("/")
    return f"{cfg.public_base_url}/{key}"


def upload_file(
    file_path: Path,
    key: str,
    content_type: str,
    cache_control: str | None = None,
) -> str:
    cfg = _load_config()
    client = _client(cfg)
    key = key.lstrip("/")
    extra: dict[str, Any] = {"ContentType": content_type}
    if cache_control:
        extra["CacheControl"] = cache_control
    client.upload_file(
        Filename=str(file_path),
        Bucket=cfg.bucket,
        Key=key,
        ExtraArgs=extra,
    )
    return public_url(key)


def upload_text(
    content: str,
    key: str,
    content_type: str = "application/rss+xml; charset=utf-8",
    cache_control: str | None = None,
) -> str:
    cfg = _load_config()
    client = _client(cfg)
    key = key.lstrip("/")
    extra: dict[str, Any] = {"ContentType": content_type}
    if cache_control:
        extra["CacheControl"] = cache_control
    client.put_object(
        Bucket=cfg.bucket,
        Key=key,
        Body=content.encode("utf-8"),
        **extra,
    )
    return public_url(key)
