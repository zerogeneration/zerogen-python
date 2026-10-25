from __future__ import annotations

import hashlib
import io
from pathlib import Path

import httpx
import pytest
from conftest import MakeClient
from fakes import (
    api_error,
    collect,
    first_page,
    generation,
    json_response,
    model,
    raises,
    run,
    upload,
)

from zerogen import has_ended

HELLO = b"hello"
HELLO_SHA256 = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
TARGET = {
    "method": "PUT",
    "url": "https://storage.example.com/u1",
    "headers": {"Content-Type": "image/png"},
    "expiresAt": "2026-10-25T00:00:00.000Z",
}


def test_create_and_wait_holds_the_create_then_waits_until_the_generation_ends(
    make_client: MakeClient,
) -> None:
    zerogen, calls = make_client(
        json_response(generation(status="running"), 202),
        json_response(generation(status="running"), 202),
        json_response(generation(status="succeeded")),
    )
    ended = run(
        zerogen.generations.create_and_wait(
            {"model": "openai/gpt-image-2/generate", "prompt": "A lighthouse at dawn"},
            idempotency_key="job-1",
        )
    )
    assert ended.status == "succeeded"
    assert [f"{call.method} {call.url} {call.headers['prefer']}" for call in calls] == [
        "POST https://api.zerogen.com/v1/generations wait=60",
        "GET https://api.zerogen.com/v1/generations/g1 wait=60",
        "GET https://api.zerogen.com/v1/generations/g1 wait=60",
    ]
    assert calls[0].json() == {
        "model": "openai/gpt-image-2/generate",
        "prompt": "A lighthouse at dawn",
    }
    assert calls[0].headers["idempotency-key"] == "job-1"
    assert calls[0].timeout["read"] == 180


def test_create_and_wait_returns_a_generation_that_ended_within_the_create(
    make_client: MakeClient,
) -> None:
    failed = generation(
        status="failed",
        error={"code": "provider_error", "message": "The provider failed.", "retryable": True},
    )
    zerogen, calls = make_client(json_response(failed))
    ended = run(zerogen.generations.create_and_wait({"model": "openai/gpt-image-2/generate"}))
    assert ended.status == "failed"
    assert ended.error is not None
    assert ended.error.code == "provider_error"
    assert len(calls) == 1


def test_reads_statuses_and_fields_it_doesnt_know_yet(make_client: MakeClient) -> None:
    zerogen, _ = make_client(json_response(generation(status="paused", priority="high")))
    later = run(zerogen.generations.get("g1"))
    assert later.status == "paused"
    assert not has_ended(later)
    assert later.model_extra == {"priority": "high"}


def test_lists_every_page_with_the_same_filters(make_client: MakeClient) -> None:
    zerogen, calls = make_client(
        json_response({"data": [generation("g1"), generation("g2")], "nextCursor": "c2"}),
        json_response({"data": [generation("g3")], "nextCursor": None}),
    )
    listed = collect(zerogen.generations.list(project_id="p1", limit=2))
    assert [item.id for item in listed] == ["g1", "g2", "g3"]
    assert [call.url for call in calls] == [
        "https://api.zerogen.com/v1/generations?projectId=p1&limit=2",
        "https://api.zerogen.com/v1/generations?projectId=p1&limit=2&cursor=c2",
    ]


def test_returns_a_list_as_its_first_page(make_client: MakeClient) -> None:
    zerogen, calls = make_client(
        json_response({"data": [model("a/b/generate")], "nextCursor": "c2"}),
        json_response({"data": [model("a/c/generate")], "nextCursor": None}),
    )
    page = first_page(zerogen.models.list(capability="video", audio=True))
    assert len(page.data) == 1
    assert page.next_cursor == "c2"
    assert page.has_next_page()
    assert len(calls) == 1
    assert calls[0].url == "https://api.zerogen.com/v1/models?capability=video&audio=true"
    last = run(page.get_next_page())
    assert [item.id for item in last.data] == ["a/c/generate"]
    assert not last.has_next_page()


def test_uploads_bytes_to_the_target_without_the_api_key_then_completes(
    make_client: MakeClient,
) -> None:
    zerogen, calls = make_client(
        json_response(upload(status="upload_required", assetId=None, upload=TARGET), 201),
        httpx.Response(200),
        json_response(upload(assetId="a1")),
    )
    ready = run(zerogen.uploads.upload(HELLO, filename="shot.PNG", project_id="p1"))
    asset_id: str = ready.asset_id
    assert asset_id == "a1"
    assert ready.status == "ready"
    assert calls[0].json() == {
        "filename": "shot.PNG",
        "contentType": "image/png",
        "sizeBytes": 5,
        "sha256": HELLO_SHA256,
        "projectId": "p1",
    }
    put = calls[1]
    assert (put.method, put.url, put.body) == ("PUT", "https://storage.example.com/u1", HELLO)
    assert put.headers["content-type"] == "image/png"
    assert put.headers["content-length"] == "5"
    assert "authorization" not in put.headers
    assert put.timeout["read"] is None
    assert calls[2].url == "https://api.zerogen.com/v1/uploads/u1/complete"


def test_streams_a_path_again_when_the_target_asks_for_a_retry(
    make_client: MakeClient, tmp_path: Path
) -> None:
    content = bytes(range(256)) * 9000
    path = tmp_path / "storyboard.png"
    path.write_bytes(content)
    zerogen, calls = make_client(
        json_response(upload(status="upload_required", assetId=None, upload=TARGET), 201),
        httpx.Response(503, headers={"Retry-After": "0"}),
        httpx.Response(200),
        json_response(upload()),
    )
    run(zerogen.uploads.upload(path))
    assert calls[0].json()["filename"] == "storyboard.png"
    assert calls[0].json()["sha256"] == hashlib.sha256(content).hexdigest()
    assert calls[1].body == content
    assert calls[2].body == content
    assert calls[2].headers["content-length"] == str(len(content))
    assert "transfer-encoding" not in calls[2].headers


def test_uploads_a_file_object_from_where_it_stands(make_client: MakeClient) -> None:
    file = io.BytesIO(b"skip:" + HELLO)
    file.seek(5)
    zerogen, calls = make_client(
        json_response(upload(status="upload_required", assetId=None, upload=TARGET), 201),
        httpx.Response(200),
        json_response(upload()),
    )
    run(zerogen.uploads.upload(file, filename="hello.png"))
    assert calls[0].json()["sizeBytes"] == 5
    assert calls[0].json()["sha256"] == HELLO_SHA256
    assert calls[1].body == HELLO


def test_reuses_an_identical_file_the_project_already_has(
    make_client: MakeClient, tmp_path: Path
) -> None:
    path = tmp_path / "clip.mov"
    path.write_bytes(HELLO)
    zerogen, calls = make_client(json_response(upload(assetId="a0")))
    with path.open("rb") as file:
        ready = run(zerogen.uploads.upload(file))
    assert ready.asset_id == "a0"
    assert calls[0].json()["filename"] == "clip.mov"
    assert calls[0].json()["contentType"] == "video/quicktime"
    assert len(calls) == 1


def test_needs_a_name_and_a_type_it_can_send(make_client: MakeClient) -> None:
    zerogen, calls = make_client()
    with pytest.raises(ValueError, match="filename"):
        run(zerogen.uploads.upload(HELLO))
    with pytest.raises(ValueError, match="content_type"):
        run(zerogen.uploads.upload(HELLO, filename="notes.txt"))
    assert calls == []


def test_reports_a_target_that_refuses_the_bytes(make_client: MakeClient) -> None:
    zerogen, calls = make_client(
        json_response(upload(status="upload_required", assetId=None, upload=TARGET), 201),
        httpx.Response(403, text="<Error><Code>AccessDenied</Code></Error>"),
    )
    error = raises(Exception, lambda: zerogen.uploads.upload(HELLO, filename="hello.png"))
    assert error.code == "unexpected_response"
    assert error.status == 403
    assert len(calls) == 2


def test_completes_an_upload_with_a_new_idempotency_key(make_client: MakeClient) -> None:
    zerogen, calls = make_client(json_response(upload()), api_error(404, "not_found"))
    run(zerogen.uploads.complete("u1"))
    raises(Exception, lambda: zerogen.uploads.get("missing"))
    assert calls[0].headers["idempotency-key"]
    assert calls[1].url == "https://api.zerogen.com/v1/uploads/missing"
