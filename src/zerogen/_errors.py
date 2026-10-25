from __future__ import annotations

import json
from typing import Any, cast

import httpx


class ZeroGenError(Exception):
    """An error response from the ZeroGen API.

    Branch on `code`, which is stable; `message` is for people and can change.
    """

    status: int
    """The HTTP status."""
    code: str
    message: str
    param: str | None
    """The request field, header or query parameter at fault."""
    retryable: bool
    """Whether sending the same request again can succeed."""
    details: dict[str, Any] | None
    request_id: str | None
    """The response's `Request-Id`; quote it when contacting support."""
    headers: httpx.Headers

    def __init__(
        self,
        message: str,
        *,
        status: int,
        code: str,
        param: str | None = None,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
        headers: httpx.Headers | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.param = param
        self.retryable = retryable
        self.details = details
        self.headers = headers if headers is not None else httpx.Headers()
        self.request_id = self.headers.get("request-id")

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"

    @classmethod
    def from_response(cls, response: httpx.Response) -> ZeroGenError:
        """Reads an error response, including one that isn't ZeroGen's JSON envelope."""
        text = response.text
        error = _envelope(text)
        if error is not None:
            param = error.get("param")
            details = error.get("details")
            return cls(
                error["message"],
                status=response.status_code,
                code=error["code"],
                param=param if isinstance(param, str) else None,
                retryable=error.get("retryable") is True,
                details=cast("dict[str, Any]", details) if isinstance(details, dict) else None,
                headers=response.headers,
            )
        return cls(
            f"HTTP {response.status_code}: {text[:200]}"
            if text
            else f"HTTP {response.status_code}",
            status=response.status_code,
            code="unexpected_response",
            retryable=response.status_code == 429 or response.status_code >= 500,
            headers=response.headers,
        )


class ZeroGenConnectionError(Exception):
    """The request got no response: the connection failed or the request timed out."""


def _envelope(text: str) -> dict[str, Any] | None:
    """The error in ZeroGen's envelope, when the body is one."""
    try:
        body: object = json.loads(text)
    except ValueError:
        return None
    error = cast("dict[str, object]", body).get("error") if isinstance(body, dict) else None
    if not isinstance(error, dict):
        return None
    error = cast("dict[str, Any]", error)
    if not isinstance(error.get("code"), str) or not isinstance(error.get("message"), str):
        return None
    return error
