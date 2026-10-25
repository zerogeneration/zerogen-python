from __future__ import annotations

import json
import math
import os
import random
import time
import uuid
from collections.abc import AsyncIterable, Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal, Protocol, TypeVar, cast

import anyio
import httpx
from typing_extensions import Self, Unpack

from ._errors import ZeroGenConnectionError, ZeroGenError
from ._options import PostRequestOptions, RequestOptions
from ._pagination import AsyncPage, AsyncPaginator, Page
from ._version import __version__
from .resources.generations import AsyncGenerations, Generations
from .resources.models import AsyncModels, Models
from .resources.uploads import AsyncUploads, Uploads
from .types import Balance, Me

DEFAULT_BASE_URL = "https://api.zerogen.com/v1"
RETRY_AFTER_MAX_SECONDS = 60.0

Result = TypeVar("Result")
Item = TypeVar("Item")
Query = Mapping[str, "str | int | bool | None"]
Method = Literal["GET", "POST"]


class ListBody(Protocol[Item]):
    @property
    def data(self) -> list[Item]: ...

    @property
    def next_cursor(self) -> str | None: ...


@dataclass(frozen=True)
class _Prepared:
    url: str
    params: dict[str, str]
    headers: httpx.Headers
    content: bytes | None
    timeout: float
    max_retries: int


class _BaseClient:
    base_url: str
    timeout: float
    """Seconds httpx waits on each step of one attempt. A request that waits on a generation
    gets its wait added."""
    max_retries: int
    """How many times to retry a connection error or a retryable response."""

    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str | None,
        timeout: float,
        max_retries: int,
        default_headers: Mapping[str, str] | None,
    ) -> None:
        api_key = api_key if api_key is not None else _env("ZEROGEN_API_KEY")
        if not api_key:
            raise ValueError("Pass api_key or set the ZEROGEN_API_KEY environment variable.")
        self._api_key = api_key
        base_url = base_url if base_url is not None else _env("ZEROGEN_BASE_URL")
        self.base_url = (base_url if base_url is not None else DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._default_headers = dict(default_headers or {})

    def _prepare(
        self,
        method: Method,
        path: str,
        query: Query | None,
        body: object | None,
        wait: int | None,
        options: RequestOptions,
    ) -> _Prepared:
        headers = httpx.Headers(
            {"Accept": "application/json", "User-Agent": f"zerogen-python/{__version__}"}
        )
        headers.update(self._default_headers)
        headers.update(options.get("headers") or {})
        headers["Authorization"] = f"Bearer {self._api_key}"
        content = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            content = json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode()
        if method == "POST":
            key = cast("PostRequestOptions", options).get("idempotency_key")
            headers["Idempotency-Key"] = key if key is not None else str(uuid.uuid4())
        if wait is not None:
            headers["Prefer"] = f"wait={wait}"
        return _Prepared(
            url=self.base_url + path,
            params={
                name: _query_value(value)
                for name, value in (query or {}).items()
                if value is not None
            },
            headers=headers,
            content=content,
            timeout=options.get("timeout", self.timeout) + (wait or 0),
            max_retries=options.get("max_retries", self.max_retries),
        )


class ZeroGen(_BaseClient):
    """A client for the ZeroGen API."""

    generations: Generations
    models: Models
    uploads: Uploads

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 120.0,
        max_retries: int = 2,
        default_headers: Mapping[str, str] | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        """Creates a client.

        Args:
            api_key: Defaults to the `ZEROGEN_API_KEY` environment variable.
            base_url: Defaults to the `ZEROGEN_BASE_URL` environment variable, then
                `https://api.zerogen.com/v1`.
            timeout: Seconds httpx waits on each step of one attempt of a request. A request
                that waits on a generation gets its wait added.
            max_retries: How many times to retry a connection error or a retryable response.
            default_headers: Headers to send with every request.
            http_client: An `httpx.Client` to send requests with. The client doesn't close it.
        """
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            default_headers=default_headers,
        )
        self._http = http_client if http_client is not None else httpx.Client()
        self._owns_http = http_client is None
        self.generations = Generations(self)
        self.models = Models(self)
        self.uploads = Uploads(self)

    def me(self, **options: Unpack[RequestOptions]) -> Me:
        """The API key, the organization it belongs to, and what it can do."""
        return self._request(Me.model_validate, "GET", "/me", options=options)

    def balance(
        self, *, project_id: str | None = None, **options: Unpack[RequestOptions]
    ) -> Balance:
        """The organization's balance and spending limits, and a project's with `project_id`."""
        return self._request(
            Balance.model_validate,
            "GET",
            "/balance",
            query={"projectId": project_id},
            options=options,
        )

    def close(self) -> None:
        """Closes the HTTP client, unless it was passed in as `http_client`."""
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _request(
        self,
        cast_to: Callable[[Any], Result],
        method: Method,
        path: str,
        *,
        query: Query | None = None,
        body: object | None = None,
        wait: int | None = None,
        options: RequestOptions,
    ) -> Result:
        prepared = self._prepare(method, path, query, body, wait, options)
        response = self._send(
            method,
            prepared.url,
            params=prepared.params,
            headers=prepared.headers,
            content=lambda: prepared.content,
            timeout=prepared.timeout,
            max_retries=prepared.max_retries,
        )
        return cast_to(response.json())

    def _list(
        self,
        cast_to: Callable[[Any], ListBody[Item]],
        path: str,
        query: Query,
        options: RequestOptions,
    ) -> Page[Item]:
        def load(cursor: str | None) -> Page[Item]:
            body = self._request(
                cast_to,
                "GET",
                path,
                query=query if cursor is None else {**query, "cursor": cursor},
                options=options,
            )
            return Page(body.data, body.next_cursor, load)

        return load(None)

    def _send(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, str] | None = None,
        headers: httpx.Headers | Mapping[str, str],
        content: Callable[[], bytes | Iterable[bytes] | None],
        timeout: float | None,
        max_retries: int,
    ) -> httpx.Response:
        """Sends a request, retrying connection errors and retryable responses, and returns the
        first successful response. A `timeout` of None sends without one."""
        attempt = 0
        while True:
            try:
                response = self._http.request(
                    method, url, params=params, headers=headers, content=content(), timeout=timeout
                )
            except httpx.TransportError as error:
                time.sleep(_connection_retry_delay(error, attempt, max_retries, timeout))
            else:
                if response.is_success:
                    return response
                time.sleep(_error_retry_delay(response, attempt, max_retries))
            attempt += 1


class AsyncZeroGen(_BaseClient):
    """An asynchronous client for the ZeroGen API."""

    generations: AsyncGenerations
    models: AsyncModels
    uploads: AsyncUploads

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 120.0,
        max_retries: int = 2,
        default_headers: Mapping[str, str] | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Creates a client.

        Args:
            api_key: Defaults to the `ZEROGEN_API_KEY` environment variable.
            base_url: Defaults to the `ZEROGEN_BASE_URL` environment variable, then
                `https://api.zerogen.com/v1`.
            timeout: Seconds httpx waits on each step of one attempt of a request. A request
                that waits on a generation gets its wait added.
            max_retries: How many times to retry a connection error or a retryable response.
            default_headers: Headers to send with every request.
            http_client: An `httpx.AsyncClient` to send requests with. The client doesn't
                close it.
        """
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            default_headers=default_headers,
        )
        self._http = http_client if http_client is not None else httpx.AsyncClient()
        self._owns_http = http_client is None
        self.generations = AsyncGenerations(self)
        self.models = AsyncModels(self)
        self.uploads = AsyncUploads(self)

    async def me(self, **options: Unpack[RequestOptions]) -> Me:
        """The API key, the organization it belongs to, and what it can do."""
        return await self._request(Me.model_validate, "GET", "/me", options=options)

    async def balance(
        self, *, project_id: str | None = None, **options: Unpack[RequestOptions]
    ) -> Balance:
        """The organization's balance and spending limits, and a project's with `project_id`."""
        return await self._request(
            Balance.model_validate,
            "GET",
            "/balance",
            query={"projectId": project_id},
            options=options,
        )

    async def aclose(self) -> None:
        """Closes the HTTP client, unless it was passed in as `http_client`."""
        if self._owns_http:
            await self._http.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def _request(
        self,
        cast_to: Callable[[Any], Result],
        method: Method,
        path: str,
        *,
        query: Query | None = None,
        body: object | None = None,
        wait: int | None = None,
        options: RequestOptions,
    ) -> Result:
        prepared = self._prepare(method, path, query, body, wait, options)
        response = await self._send(
            method,
            prepared.url,
            params=prepared.params,
            headers=prepared.headers,
            content=lambda: prepared.content,
            timeout=prepared.timeout,
            max_retries=prepared.max_retries,
        )
        return cast_to(response.json())

    def _list(
        self,
        cast_to: Callable[[Any], ListBody[Item]],
        path: str,
        query: Query,
        options: RequestOptions,
    ) -> AsyncPaginator[Item]:
        async def load(cursor: str | None = None) -> AsyncPage[Item]:
            body = await self._request(
                cast_to,
                "GET",
                path,
                query=query if cursor is None else {**query, "cursor": cursor},
                options=options,
            )
            return AsyncPage(body.data, body.next_cursor, load)

        return AsyncPaginator(load)

    async def _send(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, str] | None = None,
        headers: httpx.Headers | Mapping[str, str],
        content: Callable[[], bytes | AsyncIterable[bytes] | None],
        timeout: float | None,
        max_retries: int,
    ) -> httpx.Response:
        """Sends a request, retrying connection errors and retryable responses, and returns the
        first successful response. A `timeout` of None sends without one."""
        attempt = 0
        while True:
            try:
                response = await self._http.request(
                    method, url, params=params, headers=headers, content=content(), timeout=timeout
                )
            except httpx.TransportError as error:
                await anyio.sleep(_connection_retry_delay(error, attempt, max_retries, timeout))
            else:
                if response.is_success:
                    return response
                await anyio.sleep(_error_retry_delay(response, attempt, max_retries))
            attempt += 1


def _env(name: str) -> str | None:
    return os.environ.get(name) or None


def _query_value(value: str | int | bool) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _backoff(attempt: int) -> float:
    return min(8.0, 0.5 * 2**attempt) * (0.75 + random.random() * 0.5)


def _retry_delay(headers: httpx.Headers, attempt: int) -> float | None:
    """How long to wait before retrying: `Retry-After` when the response sets it, or no retry
    past a minute."""
    try:
        seconds = float(headers.get("retry-after", "nan"))
    except ValueError:
        seconds = math.nan
    if not math.isfinite(seconds) or seconds < 0:
        return _backoff(attempt)
    return seconds if seconds <= RETRY_AFTER_MAX_SECONDS else None


def _connection_retry_delay(
    error: httpx.TransportError, attempt: int, max_retries: int, timeout: float | None
) -> float:
    if attempt >= max_retries:
        if isinstance(error, httpx.TimeoutException) and timeout is not None:
            raise ZeroGenConnectionError(
                f"The request timed out after {timeout:g} seconds."
            ) from error
        raise ZeroGenConnectionError("The request failed to connect.") from error
    return _backoff(attempt)


def _error_retry_delay(response: httpx.Response, attempt: int, max_retries: int) -> float:
    error = ZeroGenError.from_response(response)
    delay = (
        _retry_delay(response.headers, attempt)
        if error.retryable and attempt < max_retries
        else None
    )
    if delay is None:
        raise error
    return delay
