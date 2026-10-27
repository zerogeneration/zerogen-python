from __future__ import annotations

import asyncio
import importlib.metadata
from typing import Any

import httpx
import pytest
from conftest import MakeClient
from fakes import BALANCE, ME, Fake, api_error, json_response, raises, run, run_body

from zerogen import AsyncZeroGen, ZeroGen, ZeroGenConnectionError, ZeroGenError, __version__
from zerogen._client import _backoff, _retry_delay


@pytest.mark.parametrize("client_class", [ZeroGen, AsyncZeroGen])
def test_reads_the_key_and_base_url_from_the_environment(
    monkeypatch: pytest.MonkeyPatch, client_class: type[ZeroGen] | type[AsyncZeroGen]
) -> None:
    monkeypatch.setenv("ZEROGEN_API_KEY", "zg_env_key")
    monkeypatch.setenv("ZEROGEN_BASE_URL", "https://api.zerogen.test/v1/")
    fake = Fake([json_response(ME)])
    transport = httpx.MockTransport(fake.handle)
    if client_class is ZeroGen:
        ZeroGen(http_client=httpx.Client(transport=transport)).me()
    else:
        run(AsyncZeroGen(http_client=httpx.AsyncClient(transport=transport)).me())
    assert fake.calls[0].url == "https://api.zerogen.test/v1/me"
    assert fake.calls[0].headers["authorization"] == "Bearer zg_env_key"


@pytest.mark.parametrize("client_class", [ZeroGen, AsyncZeroGen])
def test_refuses_to_start_without_a_key(
    monkeypatch: pytest.MonkeyPatch, client_class: type[ZeroGen] | type[AsyncZeroGen]
) -> None:
    monkeypatch.setenv("ZEROGEN_API_KEY", "")
    with pytest.raises(ValueError, match="ZEROGEN_API_KEY"):
        client_class()


def test_sends_get_requests_with_a_query_string_and_no_idempotency_key(
    make_client: MakeClient,
) -> None:
    zerogen, calls = make_client(json_response(BALANCE))
    balance = run(zerogen.balance(project_id="p1"))
    assert balance.currency == "USD"
    assert calls[0].url == "https://api.zerogen.com/v1/balance?projectId=p1"
    assert calls[0].headers["accept"] == "application/json"
    assert calls[0].headers["user-agent"] == f"zerogen-python/{__version__}"
    assert "idempotency-key" not in calls[0].headers


def test_gives_each_post_an_idempotency_key_and_sends_no_body_when_it_has_none(
    make_client: MakeClient,
) -> None:
    zerogen, calls = make_client(json_response(run_body()), json_response(run_body()))
    run(zerogen.runs.cancel("g1"))
    run(zerogen.runs.cancel("g1", idempotency_key="mine"))
    assert len(calls[0].headers["idempotency-key"]) == 36
    assert "content-type" not in calls[0].headers
    assert calls[0].body == b""
    assert calls[1].headers["idempotency-key"] == "mine"


def test_sends_its_headers_over_the_callers_but_not_over_the_key(
    make_client: MakeClient,
) -> None:
    zerogen, calls = make_client(json_response(ME))
    run(zerogen.me(headers={"X-Trace": "t1", "Authorization": "Bearer other"}))
    assert calls[0].headers["x-trace"] == "t1"
    assert calls[0].headers["authorization"] == "Bearer zg_test_key"


def test_raises_the_error_envelope_with_its_request_id(make_client: MakeClient) -> None:
    zerogen, _ = make_client(api_error(400, "validation_failed", param="output.count"))
    error = raises(
        ZeroGenError, lambda: zerogen.runs.create({"model": "openai/gpt-image-2/generate"})
    )
    assert (error.status, error.code, error.param, error.retryable, error.request_id) == (
        400,
        "validation_failed",
        "output.count",
        False,
        "req_test",
    )
    assert str(error) == "validation_failed: validation_failed message"


def test_retries_a_retryable_response_after_retry_after_with_the_same_idempotency_key(
    make_client: MakeClient,
) -> None:
    zerogen, calls = make_client(
        api_error(429, "rate_limited", retryable=True, headers={"Retry-After": "0"}),
        api_error(409, "idempotency_in_progress", retryable=True, headers={"Retry-After": "0"}),
        json_response(run_body(), 202),
    )
    created = run(zerogen.runs.create({"model": "openai/gpt-image-2/generate"}))
    assert created.id == "g1"
    assert len(calls) == 3
    assert len({call.headers["idempotency-key"] for call in calls}) == 1


def test_doesnt_retry_an_error_that_isnt_retryable(make_client: MakeClient) -> None:
    zerogen, calls = make_client(api_error(402, "insufficient_balance"))
    assert raises(ZeroGenError, zerogen.me).code == "insufficient_balance"
    assert len(calls) == 1


def test_doesnt_wait_for_a_retry_after_over_a_minute(make_client: MakeClient) -> None:
    zerogen, calls = make_client(
        api_error(429, "rate_limited", retryable=True, headers={"Retry-After": "120"})
    )
    assert raises(ZeroGenError, zerogen.me).code == "rate_limited"
    assert len(calls) == 1


def test_stops_retrying_after_max_retries(make_client: MakeClient) -> None:
    retry_now = {"Retry-After": "0"}
    zerogen, calls = make_client(
        api_error(500, "internal", retryable=True, headers=retry_now),
        api_error(500, "internal", retryable=True, headers=retry_now),
        max_retries=1,
    )
    error = raises(ZeroGenError, zerogen.me)
    assert (error.status, error.code) == (500, "internal")
    assert len(calls) == 2


def test_reads_a_response_that_isnt_the_error_envelope(make_client: MakeClient) -> None:
    zerogen, _ = make_client(httpx.Response(502, text="<html>Bad gateway</html>"), max_retries=0)
    error = raises(ZeroGenError, zerogen.me)
    assert (error.status, error.code, error.retryable) == (502, "unexpected_response", True)
    assert error.message == "HTTP 502: <html>Bad gateway</html>"


@pytest.mark.usefixtures("no_backoff")
def test_retries_a_connection_error_then_reports_it(make_client: MakeClient) -> None:
    zerogen, calls = make_client(
        httpx.ConnectError("refused"), httpx.ConnectError("refused"), max_retries=1
    )
    error = raises(ZeroGenConnectionError, zerogen.me)
    assert str(error) == "The request failed to connect."
    assert isinstance(error.__cause__, httpx.ConnectError)
    assert len(calls) == 2


def test_reports_a_timeout(make_client: MakeClient) -> None:
    zerogen, _ = make_client(httpx.ReadTimeout("slow"), max_retries=0)
    error = raises(ZeroGenConnectionError, lambda: zerogen.me(timeout=5))
    assert str(error) == "The request timed out after 5 seconds."


def test_adds_the_wait_to_the_timeout(make_client: MakeClient) -> None:
    zerogen, calls = make_client(json_response(run_body()), json_response(run_body()))
    run(zerogen.runs.get("g1", wait=30))
    run(zerogen.runs.get("g1", timeout=10))
    assert calls[0].headers["prefer"] == "wait=30"
    assert calls[0].timeout["read"] == 150
    assert "prefer" not in calls[1].headers
    assert calls[1].timeout["read"] == 10


def test_stops_at_once_when_the_caller_interrupts() -> None:
    def interrupt(request: httpx.Request) -> httpx.Response:
        raise KeyboardInterrupt

    fake = Fake([interrupt])
    zerogen = ZeroGen(
        api_key="zg_test_key", http_client=httpx.Client(transport=httpx.MockTransport(fake.handle))
    )
    with pytest.raises(KeyboardInterrupt):
        zerogen.me()
    assert len(fake.calls) == 1


def test_stops_at_once_when_the_task_is_cancelled() -> None:
    fake = Fake([api_error(503, "unavailable", retryable=True, headers={"Retry-After": "30"})])
    zerogen = AsyncZeroGen(
        api_key="zg_test_key",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(fake.handle)),
    )

    async def cancel_while_waiting() -> None:
        task = asyncio.create_task(zerogen.me())
        while not fake.calls:
            await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(asyncio.wait_for(cancel_while_waiting(), timeout=5))
    assert len(fake.calls) == 1


def test_encodes_each_segment_of_a_model_id_into_the_path(make_client: MakeClient) -> None:
    detail: dict[str, Any] = {
        "id": "openai/gpt-image-2/generate",
        "name": "GPT Image 2",
        "capability": "image",
        "operation": "generate",
        "status": "active",
        "sunsetAt": None,
        "requestSchema": {},
    }
    zerogen, calls = make_client(json_response(detail))
    run(zerogen.models.get("openai/gpt-image-2/generate"))
    assert calls[0].url == "https://api.zerogen.com/v1/models/openai/gpt-image-2/generate"


def test_waits_out_retry_after_or_backs_off() -> None:
    assert _retry_delay(httpx.Headers({"Retry-After": "3"}), 0) == 3
    assert _retry_delay(httpx.Headers({"Retry-After": "61"}), 0) is None
    for headers in [{}, {"Retry-After": "soon"}, {"Retry-After": "-1"}]:
        delay = _retry_delay(httpx.Headers(headers), 1)
        assert delay is not None
        assert 0.75 <= delay <= 1.25
    assert 6 <= _backoff(10) <= 10


def test_states_the_packages_version() -> None:
    assert __version__ == importlib.metadata.version("zerogen")
