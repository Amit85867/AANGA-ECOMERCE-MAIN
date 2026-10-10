"""A small read-through cache for the public catalogue endpoints.

The home page and shop grid are read far more often than they change, and every
visitor asks for the same handful of responses. Caching the JSON for a short
time takes those reads off the database.

Backed by Redis when one is configured (``CACHE_REDIS_URL``, or
``RATELIMIT_STORAGE_URI`` when that is a redis URL), so every worker and
instance shares one cache and sees an invalidation at once. Without Redis each
process keeps its own small dictionary; an invalidation then reaches the other
processes only when their entries expire, so the TTL is the worst-case staleness.

Invalidation is by version: every key embeds a counter, and any admin write
bumps it, which orphans all existing entries in one step. Nothing has to know
which product affects which listing.

A cache failure is never an outage: any Redis error falls through to computing
the response normally.
"""
import json
import time
from functools import wraps

from flask import current_app, jsonify, request

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_VERSION_KEY = "aanga:cache:version"
_MAX_LOCAL_ENTRIES = 500

_local = {}                      # key -> (expires_at, payload)
_local_version = {"value": 0}
_redis = {"client": None, "checked": False}


def _client():
    """The shared Redis client, or None when Redis is not configured."""
    if _redis["checked"]:
        return _redis["client"]
    _redis["checked"] = True

    url = current_app.config.get("CACHE_REDIS_URL") or ""
    if not url:
        limiter_uri = str(current_app.config.get("RATELIMIT_STORAGE_URI") or "")
        if limiter_uri.startswith(("redis://", "rediss://")):
            url = limiter_uri
    if not url:
        return None

    try:
        import redis
        client = redis.Redis.from_url(url, socket_timeout=0.25, socket_connect_timeout=0.25)
        client.ping()
        _redis["client"] = client
    except Exception:  # noqa: BLE001
        current_app.logger.warning("CACHE_REDIS_UNAVAILABLE falling back to in-process cache")
    return _redis["client"]


def _version():
    client = _client()
    if client is not None:
        try:
            return int(client.get(_VERSION_KEY) or 0)
        except Exception:  # noqa: BLE001
            pass
    return _local_version["value"]


def invalidate():
    """Drop every cached catalogue response."""
    _local_version["value"] += 1
    _local.clear()
    client = _client()
    if client is not None:
        try:
            client.incr(_VERSION_KEY)
        except Exception:  # noqa: BLE001
            current_app.logger.warning("CACHE_INVALIDATE_FAILED")


def get_or_set(name, ttl, compute):
    """Return ``compute()``'s JSON-serialisable result, cached for ``ttl`` seconds."""
    if not current_app.config.get("CACHE_ENABLED", True):
        return compute()

    key = f"aanga:cache:v{_version()}:{name}"
    client = _client()

    if client is not None:
        try:
            hit = client.get(key)
            if hit is not None:
                return json.loads(hit)
        except Exception:  # noqa: BLE001
            client = None   # skip the write too; behave as if uncached
    else:
        entry = _local.get(key)
        if entry and entry[0] > time.monotonic():
            return entry[1]

    value = compute()

    if client is not None:
        try:
            client.setex(key, ttl, json.dumps(value, default=str))
        except Exception:  # noqa: BLE001
            pass
    else:
        if len(_local) >= _MAX_LOCAL_ENTRIES:
            _local.clear()
        _local[key] = (time.monotonic() + ttl, value)
    return value


def request_key(prefix):
    """A cache name for the current request: path plus its sorted query string."""
    query = "&".join(f"{k}={v}" for k, v in sorted(request.args.items(multi=True)))
    return f"{prefix}:{request.path}?{query}"


class _NotCacheable(Exception):
    def __init__(self, response):
        self.response = response


def cached_view(ttl):
    """Cache a public GET view's 200 JSON response, keyed by path and query.

    Only for responses that are the same for every visitor. Anything other
    than a 200 is passed straight through and never stored.
    """
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            def compute():
                result = view(*args, **kwargs)
                response, status = result if isinstance(result, tuple) else (result, 200)
                if status != 200:
                    raise _NotCacheable(result)
                return response.get_json()

            try:
                body = get_or_set(request_key(view.__name__), ttl, compute)
            except _NotCacheable as passthrough:
                return passthrough.response
            return jsonify(body), 200
        return wrapper
    return decorator


def reset_for_tests():
    _local.clear()
    _local_version["value"] = 0
    _redis.update(client=None, checked=False)


def init_app(app):
    @app.after_request
    def _invalidate_on_admin_write(resp):
        # Any successful admin change may alter what the storefront shows.
        # Coarse on purpose: a wrongly kept entry shows customers stale prices,
        # a wrongly dropped one costs a single query.
        if (
            request.method in WRITE_METHODS
            and request.path.startswith("/api/admin/")
            and 200 <= resp.status_code < 300
        ):
            invalidate()
        return resp
