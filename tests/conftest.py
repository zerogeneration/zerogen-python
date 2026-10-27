from __future__ import annotations

from typing import Protocol

import httpx
import pytest
from fakes import Call, Client, Fake, Reply

from zerogen import AsyncZeroGen, ZeroGen


class MakeClient(Protocol):
    def __call__(
        self,
        *replies: Reply,
        max_retries: int = 2,
        default_headers: dict[str, str] | None = None,
        http_headers: dict[str, str] | None = None,
    ) -> tuple[Client, list[Call]]: ...


@pytest.fixture(params=["sync", "async"])
def make_client(request: pytest.FixtureRequest) -> MakeClient:
    """Makes a ZeroGen or an AsyncZeroGen, once each, that sends to a scripted transport."""

    def make(
        *replies: Reply,
        max_retries: int = 2,
        default_headers: dict[str, str] | None = None,
        http_headers: dict[str, str] | None = None,
    ) -> tuple[Client, list[Call]]:
        fake = Fake(replies)
        transport = httpx.MockTransport(fake.handle)
        if request.param == "sync":
            client: Client = ZeroGen(
                api_key="zg_test_key",
                max_retries=max_retries,
                default_headers=default_headers,
                http_client=httpx.Client(transport=transport, headers=http_headers),
            )
        else:
            client = AsyncZeroGen(
                api_key="zg_test_key",
                max_retries=max_retries,
                default_headers=default_headers,
                http_client=httpx.AsyncClient(transport=transport, headers=http_headers),
            )
        return client, fake.calls

    return make


@pytest.fixture
def no_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    def backoff(attempt: int) -> float:
        return 0.0

    monkeypatch.setattr("zerogen._client._backoff", backoff)
