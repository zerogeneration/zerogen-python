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


def run_body(id: str = "g1", status: str = "queued", **fields: Any) -> dict[str, Any]:
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


def asset(id: str = "a1", **fields: Any) -> dict[str, Any]:
    return {
        "id": id,
        "projectId": "p1",
        "name": "Lighthouse",
        "type": "image",
        "origin": "generated",
        "mimeType": "image/png",
        "sizeBytes": 5,
        "width": 1024,
        "height": 1024,
        "durationMs": None,
        "favorite": False,
        "labels": [],
        "runId": "g1",
        "outputIndex": 0,
        "createdAt": "2026-10-25T00:00:00.000Z",
        "preview": None,
        **fields,
    }


def preview(id: str = "a1", *, clip: bool = False) -> dict[str, Any]:
    """An asset's preview, with fake signed URLs."""
    signed = "?X-Amz-Expires=300&X-Amz-Signature=fake"
    return {
        "image96Url": f"https://storage.example.com/{id}-96.webp{signed}",
        "image512Url": f"https://storage.example.com/{id}-512.webp{signed}",
        "videoUrl": f"https://storage.example.com/{id}-clip.webm{signed}" if clip else None,
        "expiresAt": "2026-10-25T00:05:00.000Z",
    }


def run_output(index: int = 0, **asset_fields: Any) -> dict[str, Any]:
    """A run's succeeded output, with its asset."""
    return {
        "index": index,
        "status": "succeeded",
        "asset": {
            "id": f"a{index + 1}",
            "mimeType": "image/png",
            "width": 1024,
            "height": 1024,
            "durationMs": None,
            "preview": None,
            **asset_fields,
        },
        "error": None,
    }


def download_link(url: str) -> dict[str, Any]:
    return {
        "assetId": "a1",
        "projectId": "p1",
        "url": url,
        "expiresAt": "2026-10-25T00:05:00.000Z",
        "filename": "lighthouse.png",
        "mimeType": "image/png",
        "sizeBytes": 5,
    }


def page(*items: dict[str, Any], next_cursor: str | None = None) -> dict[str, Any]:
    return {"data": list(items), "nextCursor": next_cursor}


FOLDER = {
    "id": "f1",
    "projectId": "p1",
    "parentId": None,
    "name": "Shots",
    "createdAt": "2026-10-25T00:00:00.000Z",
}

LABEL = {"id": "l1", "name": "Hero", "description": None, "color": "#ef4444", "archived": False}

ME = {
    "apiKey": {
        "id": "k1",
        "name": "Test",
        "mode": "test",
        "scopes": ["runs:create"],
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
