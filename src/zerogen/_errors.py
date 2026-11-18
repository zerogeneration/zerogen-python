from __future__ import annotations

import json
import re
from typing import Any, Literal, TypeAlias, cast

import httpx

ErrorReason: TypeAlias = (
    Literal[
        "request_limit",
        "running_cap",
        "platform_capacity",
        "url_import_limit",
        "scope_required",
        "role_required",
        "not_creator",
        "feature_not_enabled",
        "early_access",
        "test_key_sandbox",
        "browser_request",
    ]
    | str
)
"""Why the API refused a request, in a `rate_limited` or `permission_denied` error's
`details.reason`. The API can add reasons, so handle one you don't know as you would the error
without a reason."""


class ZeroGenError(Exception):
    """An error response from the ZeroGen API.

    Branch on `code`, which is stable, and on `reason` for `rate_limited` and
    `permission_denied`; `message` is for people and can change.
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
    """More facts about the error, such as `currentVersion` on a `version_conflict`; each code
    says which it carries."""
    reason: ErrorReason | None
    """`details.reason`: which limit a `rate_limited` error reached, or why a
    `permission_denied` error refused the request. None when the error carries none."""
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
        reason = (details or {}).get("reason")
        self.reason = reason if isinstance(reason, str) else None
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


def storage_error(response: httpx.Response) -> ZeroGenError:
    """An error response from signed storage, with only the S3 error's `Code` and `Message`:
    never the rest of the body, which can echo the request's signature."""

    def field(name: str) -> str | None:
        match = re.search(f"<{name}>([^<]{{1,200}})</{name}>", response.text)
        return match.group(1) if match else None

    reason = ": ".join(value for value in (field("Code"), field("Message")) if value)
    return ZeroGenError(
        f"Storage answered HTTP {response.status_code}" + (f": {reason}" if reason else ""),
        status=response.status_code,
        code="unexpected_response",
        retryable=response.status_code == 429 or response.status_code >= 500,
        headers=response.headers,
    )


class ZeroGenConnectionError(Exception):
    """The request got no response: the connection failed or the request timed out."""


class WaitCancelledError(Exception):
    """`ZeroGen.runs.wait_for` stopped waiting because its `cancel` event was set. The run
    keeps running; to stop it, call `runs.cancel`."""

    run_id: str

    def __init__(self, run_id: str) -> None:
        super().__init__(f"Stopped waiting for run {run_id}; it keeps running.")
        self.run_id = run_id


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
