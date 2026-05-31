"""Synchronous Upstash Redis REST client for shared slot cache."""

from __future__ import annotations

import json
import logging
import os
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)

UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")

HEADERS: dict[str, str] = (
    {"Authorization": f"Bearer {UPSTASH_TOKEN}"} if UPSTASH_TOKEN else {}
)

_REQUEST_TIMEOUT = 10.0


def _base_url() -> str:
    return (UPSTASH_URL or "").rstrip("/")


def _redis_ready() -> bool:
    return bool(UPSTASH_URL and UPSTASH_TOKEN)


def _encode_key(key: str) -> str:
    return quote(key, safe="")


def redis_get(key: str):
    if not _redis_ready():
        return None
    try:
        res = requests.get(
            f"{_base_url()}/get/{_encode_key(key)}",
            headers=HEADERS,
            timeout=_REQUEST_TIMEOUT,
        )
        res.raise_for_status()
        data = res.json()
    except (requests.RequestException, ValueError, json.JSONDecodeError) as e:
        logger.warning("redis_get failed: %s", e)
        return None
    raw = data.get("result")
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError) as e:
        logger.warning("redis_get could not decode JSON: %s", e)
        return None


def redis_set(key: str, value, ttl: int = 60) -> None:
    if not _redis_ready():
        return
    try:
        payload = json.dumps(value)
        res = requests.post(
            f"{_base_url()}/set/{_encode_key(key)}",
            headers=HEADERS,
            params={"EX": ttl} if ttl else None,
            data=payload.encode("utf-8"),
            timeout=_REQUEST_TIMEOUT,
        )
        res.raise_for_status()
    except (requests.RequestException, TypeError, ValueError) as e:
        logger.warning("redis_set failed: %s", e)


def redis_delete(key: str) -> None:
    if not _redis_ready():
        return
    try:
        res = requests.get(
            f"{_base_url()}/del/{_encode_key(key)}",
            headers=HEADERS,
            timeout=_REQUEST_TIMEOUT,
        )
        res.raise_for_status()
    except requests.RequestException as e:
        logger.warning("redis_delete failed: %s", e)


def _scan_cursor_done(cursor) -> bool:
    """Upstash may return the next cursor as int or str (finished when zero)."""
    try:
        return int(cursor) == 0
    except (TypeError, ValueError):
        return str(cursor) in ("0", "")


def redis_delete_pattern(pattern: str) -> None:
    if not _redis_ready():
        return
    # Upstash REST: SCAN must be sent with MATCH/COUNT in the command body. A GET to
    # /scan/{cursor} with query params does not reliably apply MATCH, so pattern deletes
    # could miss ``slots:{doctor_id}:*`` keys and leave stale cache entries.
    base = _base_url()
    cursor: str = "0"
    post_headers = {**HEADERS, "Content-Type": "application/json"}
    while True:
        try:
            res = requests.post(
                base,
                headers=post_headers,
                json=["SCAN", cursor, "MATCH", pattern, "COUNT", 100],
                timeout=_REQUEST_TIMEOUT,
            )
            res.raise_for_status()
            data = res.json()
        except (requests.RequestException, ValueError, json.JSONDecodeError) as e:
            logger.warning("redis_delete_pattern scan failed: %s", e)
            break
        err = data.get("error")
        if err:
            logger.warning("redis_delete_pattern scan error: %s", err)
            break
        result = data.get("result")
        if not result or not isinstance(result, (list, tuple)) or len(result) < 2:
            break
        next_cursor, keys = result[0], result[1] or []
        cursor = str(next_cursor)
        for key in keys:
            try:
                dres = requests.get(
                    f"{base}/del/{_encode_key(key)}",
                    headers=HEADERS,
                    timeout=_REQUEST_TIMEOUT,
                )
                dres.raise_for_status()
            except requests.RequestException as e:
                logger.warning("redis_delete_pattern del failed: %s", e)
        if _scan_cursor_done(next_cursor):
            break
