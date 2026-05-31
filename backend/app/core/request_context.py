"""Per-request identifiers for tracing (set by ASGI middleware, read in services/logging)."""

from __future__ import annotations

from contextvars import ContextVar, Token

_request_id_cv: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    return _request_id_cv.get()


def bind_request_id(value: str | None) -> Token:
    """Attach ``value`` as the trace id for the remainder of this context; caller must reset the token."""

    return _request_id_cv.set(value)


def reset_request_id(token: Token) -> None:
    _request_id_cv.reset(token)
