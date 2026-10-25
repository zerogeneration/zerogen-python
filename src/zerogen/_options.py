from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from typing_extensions import TypedDict


class RequestOptions(TypedDict, total=False):
    """Options that every method takes as keyword arguments."""

    timeout: float
    """Overrides the client's `timeout` for this request."""
    max_retries: int
    """Overrides the client's `max_retries` for this request."""
    headers: Mapping[str, str]
    """Headers to send with this request."""


class PostRequestOptions(RequestOptions, total=False):
    """Options that every method sending a `POST` takes as keyword arguments."""

    idempotency_key: str
    """Each call sends a new random key by default and reuses it on that call's retries; pass
    your own to make a retry across calls safe."""


def without_idempotency_key(options: PostRequestOptions) -> RequestOptions:
    rest = dict(options)
    rest.pop("idempotency_key", None)
    return cast(RequestOptions, rest)
