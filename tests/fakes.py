"""A scripted httpx transport and the API responses the tests send through it."""

from __future__ import annotations

import asyncio
import inspect
import json
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import Any, TypeVar, cast

import httpx
import pytest

from zerogen import AsyncPage, AsyncPaginator, AsyncZeroGen, Page, ZeroGen

T = TypeVar("T")
Reply = httpx.Response | Exception | Callable[[httpx.Request], httpx.Response]
Client = ZeroGen | AsyncZeroGen


@dataclass
class Call:
    method: str
    url: str
    headers: httpx.Headers
    body: bytes
    timeout: dict[str, float | None]

    def json(self) -> Any:
        return json.loads(self.body)


class Fake:
    """An httpx transport that answers from a script of replies and records each request."""

    def __init__(self, replies: Iterable[Reply]) -> None:
        self.replies = list(replies)
        self.calls: list[Call] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(
            Call(
                method=request.method,
                url=str(request.url),
                headers=request.headers,
                body=request.content,
                timeout=request.extensions.get("timeout", {}),
            )
        )
        if not self.replies:
            raise AssertionError(f"Unexpected request: {request.method} {request.url}")
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply(request) if callable(reply) else reply


def run(value: T | Awaitable[T]) -> T:
    """Returns a sync client's result, or runs an async client's to completion."""
    if inspect.isawaitable(value):
        awaitable = cast("Awaitable[T]", value)

        async def wait() -> T:
            return await awaitable

        return asyncio.run(wait())
    return cast("T", value)


def raises(error: type[BaseException], call: Callable[[], object]) -> Any:
    """Calls a sync or async method and returns the error it raised."""
    with pytest.raises(error) as caught:
        run(call())
    return caught.value


def first_page(pages: Page[T] | AsyncPaginator[T]) -> Page[T] | AsyncPage[T]:
    """A sync list, or the first page of an async one."""
    return pages if isinstance(pages, Page) else run(pages)


def collect(items: Any) -> list[Any]:
    """Every item of a sync list, or of an async one."""
    if hasattr(items, "__aiter__"):

        async def gather() -> list[Any]:
            return [item async for item in items]

        return asyncio.run(gather())
    return list(items)


def json_response(
    body: Any, status: int = 200, headers: dict[str, str] | None = None
) -> httpx.Response:
    return httpx.Response(status, json=body, headers={"Request-Id": "req_test", **(headers or {})})


def api_error(
    status: int,
    code: str,
    *,
    retryable: bool = False,
    param: str | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    error: dict[str, Any] = {"code": code, "message": f"{code} message", "retryable": retryable}
    if param is not None:
        error["param"] = param
    return json_response({"error": error}, status, headers)


def generation(id: str = "g1", status: str = "queued", **fields: Any) -> dict[str, Any]:
    return {
        "id": id,
        "projectId": "p1",
        "model": "openai/gpt-image-2/generate",
        "modelVersion": None,
        "status": status,
        "outputs": [],
        "error": None,
        "billing": {
            "mode": "test",
            "state": None,
            "quotedMicroUsd": None,
            "heldMicroUsd": None,
            "chargedMicroUsd": None,
        },
        "createdAt": "2026-10-25T00:00:00.000Z",
        "startedAt": None,
        "finishedAt": None,
        **fields,
    }


def model(id: str) -> dict[str, Any]:
    return {
        "id": id,
        "name": id,
        "capability": "image",
        "operation": "generate",
        "status": "active",
        "sunsetAt": None,
    }


def upload(id: str = "u1", **fields: Any) -> dict[str, Any]:
    return {
        "id": id,
        "projectId": "p1",
        "status": "ready",
        "assetId": "a1",
        "upload": None,
        **fields,
    }


ME = {
    "apiKey": {
        "id": "k1",
        "name": "Test",
        "mode": "test",
        "scopes": ["generations:create"],
        "createdAt": "2026-10-25T00:00:00.000Z",
        "expiresAt": None,
    },
    "organization": {"id": "o1", "name": "Org"},
    "user": {"id": "u1"},
    "sandbox": {"projectId": "p1"},
}

BALANCE = {
    "currency": "USD",
    "balanceMicroUsd": 0,
    "heldMicroUsd": None,
    "availableMicroUsd": 0,
    "unlimited": False,
    "limits": {"organizationMonthly": None, "projectMonthly": None},
}
