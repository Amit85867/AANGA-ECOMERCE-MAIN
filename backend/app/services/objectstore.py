"""S3-compatible object storage.

Product images live in Neon Object Storage, which speaks S3. Nothing here is
Neon-specific: it is plain boto3 against an ``endpoint_url`` with path-style
addressing, so any S3-compatible store (Neon, MinIO, Cloudflare R2, Backblaze,
AWS itself) works by changing environment variables alone.

Configured by:

====================== ==========================================
S3_ENDPOINT_URL        e.g. https://<branch>.storage.<region>.aws.neon.tech
S3_BUCKET              bucket name, e.g. product-images
S3_ACCESS_KEY_ID       Neon: the credential's token id
S3_SECRET_ACCESS_KEY   Neon: the credential's s3_secret_access_key
S3_REGION              e.g. ap-southeast-1
S3_PUBLIC_BASE_URL     what a browser fetches; defaults to endpoint/bucket
S3_FORCE_PATH_STYLE    default true; Neon requires it
====================== ==========================================

Two things worth knowing about Neon's flavour:

* The endpoint **embeds the branch id**, so dev, test and production each have
  their own endpoint. One more reason this is configured per environment and
  never hard-coded.
* A ``public_read`` bucket serves objects at ``<endpoint>/<bucket>/<key>`` with
  no credentials, which is what the storefront uses. Objects are served with
  whatever Content-Type they were uploaded with, so always set it explicitly:
  an image stored as ``binary/octet-stream`` will download instead of render.
"""
import threading

from flask import current_app

try:  # boto3 is a hard dependency in requirements.txt; guard so import-time
    import boto3  # failures surface as a clear StorageError, not a traceback.
    from botocore.config import Config
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:  # pragma: no cover - only when deps are not installed
    boto3 = None
    Config = None

    class BotoCoreError(Exception):
        pass

    class ClientError(Exception):
        pass


class StorageError(RuntimeError):
    """Storage was configured but would not accept the operation."""


# Required before the app will call itself "configured for object storage".
REQUIRED_SETTINGS = (
    "S3_ENDPOINT_URL",
    "S3_BUCKET",
    "S3_ACCESS_KEY_ID",
    "S3_SECRET_ACCESS_KEY",
)

# One client per process, keyed by the settings it was built from, so a config
# change in a test does not get a stale client.
_lock = threading.Lock()
_cache = {"key": None, "client": None}


def _cfg(config=None):
    return config if config is not None else current_app.config


def is_configured(config=None):
    cfg = _cfg(config)
    return all(cfg.get(name) for name in REQUIRED_SETTINGS)


def missing_settings(config=None):
    cfg = _cfg(config)
    return [name for name in REQUIRED_SETTINGS if not cfg.get(name)]


def client(config=None):
    cfg = _cfg(config)
    if not is_configured(cfg):
        raise StorageError(
            "Object storage is not configured: "
            + ", ".join(missing_settings(cfg))
            + " must be set."
        )
    if boto3 is None:  # pragma: no cover
        raise StorageError("boto3 is not installed (pip install -r requirements.txt).")

    key = tuple(str(cfg.get(name)) for name in REQUIRED_SETTINGS) + (
        str(cfg.get("S3_REGION")),
        str(cfg.get("S3_FORCE_PATH_STYLE")),
    )
    with _lock:
        if _cache["key"] == key and _cache["client"] is not None:
            return _cache["client"]
        style = "path" if cfg.get("S3_FORCE_PATH_STYLE", True) else "virtual"
        built = boto3.client(
            "s3",
            endpoint_url=cfg["S3_ENDPOINT_URL"],
            aws_access_key_id=cfg["S3_ACCESS_KEY_ID"],
            aws_secret_access_key=cfg["S3_SECRET_ACCESS_KEY"],
            region_name=cfg.get("S3_REGION") or "auto",
            config=Config(
                s3={"addressing_style": style},
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
                connect_timeout=15,
                read_timeout=60,
            ),
        )
        _cache.update(key=key, client=built)
        return built


def reset_client():
    """Drop the cached client. Used by tests that change the configuration."""
    with _lock:
        _cache.update(key=None, client=None)


def public_base_url(config=None):
    cfg = _cfg(config)
    explicit = cfg.get("S3_PUBLIC_BASE_URL")
    if explicit:
        return explicit.rstrip("/")
    return f"{cfg['S3_ENDPOINT_URL'].rstrip('/')}/{cfg['S3_BUCKET']}"


def public_url(key, config=None):
    return f"{public_base_url(config)}/{key.lstrip('/')}"


def key_for_url(url, config=None):
    """The object key a public URL points at, or None if it is not ours."""
    if not url:
        return None
    base = public_base_url(config) + "/"
    if url.startswith(base):
        return url[len(base):]
    return None


def put_bytes(key, data, content_type):
    """Store bytes and return the public URL.

    Content-Type is always set: an object served as binary/octet-stream makes a
    browser download the file instead of rendering the image.
    """
    cfg = _cfg()
    try:
        client().put_object(
            Bucket=cfg["S3_BUCKET"],
            Key=key,
            Body=data,
            ContentType=content_type,
            # Content-addressed names, so a long cache is safe and the
            # storefront's srcset copies are cheap to serve.
            CacheControl="public, max-age=31536000, immutable",
        )
    except (BotoCoreError, ClientError) as exc:
        raise StorageError(f"Object storage rejected the upload: {exc}") from exc
    return public_url(key, cfg)


def delete_keys(keys):
    """Delete objects, ignoring ones that are already gone. Best effort."""
    cfg = _cfg()
    keys = [k for k in keys if k]
    if not keys:
        return 0
    deleted = 0
    try:
        c = client()
        for k in keys:
            try:
                c.delete_object(Bucket=cfg["S3_BUCKET"], Key=k)
                deleted += 1
            except ClientError as exc:  # a missing key is not a failure
                if exc.response.get("Error", {}).get("Code") not in ("NoSuchKey", "404"):
                    raise
    except (BotoCoreError, ClientError) as exc:
        current_app.logger.warning("MEDIA_DELETE_FAILED keys=%s err=%s", keys, exc)
    return deleted


def list_keys(prefix="", limit=1000):
    """Object keys under a prefix. Used by the media library and the migration."""
    cfg = _cfg()
    out = []
    try:
        paginator = client().get_paginator("list_objects_v2")
        for page in paginator.paginate(
            Bucket=cfg["S3_BUCKET"], Prefix=prefix,
            PaginationConfig={"MaxItems": limit},
        ):
            for item in page.get("Contents", []):
                out.append(item["Key"])
    except (BotoCoreError, ClientError) as exc:
        raise StorageError(f"Could not list objects: {exc}") from exc
    return out


def exists(key):
    cfg = _cfg()
    try:
        client().head_object(Bucket=cfg["S3_BUCKET"], Key=key)
        return True
    except ClientError:
        return False
    except BotoCoreError as exc:
        raise StorageError(f"Could not check {key}: {exc}") from exc
