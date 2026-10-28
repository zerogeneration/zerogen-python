from __future__ import annotations

import io
import logging
from collections.abc import AsyncIterator, Callable, Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn

import anyio
import httpx
import pytest
from conftest import MakeClient
from fakes import (
    FOLDER,
    LABEL,
    Client,
    asset,
    download_link,
    first_page,
    json_response,
    page,
    preview,
    raises,
    run,
)

from zerogen import ZeroGenConnectionError, ZeroGenError
from zerogen.resources import assets as assets_module

API = "https://api.zerogen.com/v1"
SIGNED = "https://storage.example.com/a1.png?X-Amz-Expires=300&X-Amz-Signature=first"
RESIGNED = "https://storage.example.com/a1.png?X-Amz-Expires=300&X-Amz-Signature=second"
EXPIRED = "<Error><Code>AccessDenied</Code><Message>Request has expired</Message></Error>"
HELLO = b"hello"
FOLDER_CHANGE = {"folderId": "f1", "updatedAssetIds": ["a1"], "skippedAssetIds": []}
LABEL_CHANGE = {"labelId": "l1", "projectId": "p1", "assetIds": ["a1"], "assigned": True}
LINEAGE: dict[str, Any] = {
    "asset": None,
    "sources": [],
    "uses": [],
    "edges": [],
    "truncated": {"sources": False, "uses": False},
}
ROUTES: list[tuple[Callable[[Client], object], str, Any, dict[str, Any]]] = [
    (
        lambda z: z.assets.get("a1"),
        "GET /assets/a1",
        None,
        asset(prompt="A lighthouse", promptTruncated=False),
    ),
    (lambda z: z.assets.lineage("a1"), "GET /assets/a1/lineage", None, LINEAGE),
    (
        lambda z: z.assets.folders("a1"),
        "GET /assets/a1/folders",
        None,
        {"assetId": "a1", "projectId": "p1", "folders": [], "truncated": False},
    ),
    (lambda z: z.assets.get_download("a1"), "GET /assets/a1/download", None, download_link(SIGNED)),
    (
        lambda z: z.assets.update("p1", "a1", {"favorite": True}),
        "PATCH /projects/p1/assets/a1",
        {"favorite": True},
        {"id": "a1", "projectId": "p1", "favorite": True},
    ),
    (
        lambda z: z.folders.create("p1", {"name": "Shots"}),
        "POST /projects/p1/folders",
        {"name": "Shots"},
        FOLDER,
    ),
    (
        lambda z: z.folders.update("p1", "f1", {"parentId": None}),
        "PATCH /projects/p1/folders/f1",
        {"parentId": None},
        FOLDER,
    ),
    (
        lambda z: z.folders.add_assets("p1", "f1", {"assetIds": ["a1"]}),
        "POST /projects/p1/folders/f1/assets",
        {"assetIds": ["a1"]},
        FOLDER_CHANGE,
    ),
    (
        lambda z: z.folders.move_assets("p1", "f1", {"assetIds": ["a1"], "fromFolderId": "f0"}),
        "POST /projects/p1/folders/f1/assets/move",
        {"assetIds": ["a1"], "fromFolderId": "f0"},
        FOLDER_CHANGE,
    ),
    (
        lambda z: z.folders.remove_assets("p1", "f1", {"assetIds": ["a1"]}),
        "POST /projects/p1/folders/f1/assets/remove",
        {"assetIds": ["a1"]},
        FOLDER_CHANGE,
    ),
    (lambda z: z.labels.create({"name": "Hero"}), "POST /labels", {"name": "Hero"}, LABEL),
    (
        lambda z: z.labels.update("l1", {"name": "Hero", "description": "", "color": "#ef4444"}),
        "PUT /labels/l1",
        {"name": "Hero", "description": "", "color": "#ef4444"},
        LABEL,
    ),
    (lambda z: z.labels.archive("l1"), "POST /labels/l1/archive", None, LABEL),
    (lambda z: z.labels.restore("l1"), "POST /labels/l1/restore", None, LABEL),
    (
        lambda z: z.labels.add_assets("p1", "l1", {"assetIds": ["a1"]}),
        "POST /projects/p1/labels/l1/assets",
        {"assetIds": ["a1"]},
        LABEL_CHANGE,
    ),
    (
        lambda z: z.labels.remove_assets("p1", "l1", {"assetIds": ["a1"]}),
        "POST /projects/p1/labels/l1/assets/remove",
        {"assetIds": ["a1"]},
        LABEL_CHANGE,
    ),
    (
        lambda z: z.skills.get("s1", project_id="p1"),
        "GET /skills/s1?projectId=p1",
        None,
        {"id": "s1", "version": 2, "name": "Storyboards", "description": "Boards", "body": "Draw"},
    ),
]


class Broken(httpx.SyncByteStream, httpx.AsyncByteStream):
    """A response body that drops the connection partway."""

    def __init__(self) -> None:
        self.closed = False

    def __iter__(self) -> Iterator[bytes]:
        yield HELLO[:2]
        raise httpx.ReadError("The connection dropped.")

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield HELLO[:2]
        raise httpx.ReadError("The connection dropped.")

    def close(self) -> None:
        self.closed = True

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.parametrize(("call", "route", "body", "reply"), ROUTES, ids=[r[1] for r in ROUTES])
def test_sends_each_library_request_to_its_route(
    make_client: MakeClient,
    call: Callable[[Client], object],
    route: str,
    body: Any,
    reply: dict[str, Any],
) -> None:
    zerogen, calls = make_client(json_response(reply))
    run(call(zerogen))
    method, path = route.split(" ")
    assert (calls[0].method, calls[0].url) == (method, API + path)
    assert (calls[0].json() if calls[0].body else None) == body
    assert ("idempotency-key" in calls[0].headers) == (method == "POST")


def test_lists_library_collections_with_their_filters(make_client: MakeClient) -> None:
    zerogen, calls = make_client(*[json_response(page()) for _ in range(6)])
    first_page(zerogen.projects.list())
    first_page(zerogen.folders.list("p1", limit=100))
    first_page(zerogen.naming_presets.list("p1", cursor="c1"))
    first_page(zerogen.skills.list(project_id="p1"))
    first_page(zerogen.labels.list(include_archived=True))
    first_page(zerogen.labels.list(include_archived=False, limit=5))
    assert [call.url for call in calls] == [
        f"{API}/projects",
        f"{API}/projects/p1/folders?limit=100",
        f"{API}/projects/p1/naming-presets?cursor=c1",
        f"{API}/skills?projectId=p1",
        f"{API}/labels?includeArchived=true",
        f"{API}/labels?includeArchived=false&limit=5",
    ]


def test_searches_assets_with_repeated_filters_and_favorites_only_when_asked(
    make_client: MakeClient,
) -> None:
    zerogen, calls = make_client(
        json_response(page(asset(), next_cursor="c2")), json_response(page())
    )
    found = first_page(
        zerogen.assets.search(
            project_id="p1",
            folder_id="unfiled",
            favorite=True,
            label_id=["l1", "l2"],
            type="video",
            resolution="4k",
            sort="oldest",
        )
    )
    assert found.data[0].run_id == "g1"
    first_page(zerogen.assets.search(favorite=False, label_id=[]))
    assert [call.url for call in calls] == [
        f"{API}/assets?projectId=p1&folderId=unfiled&favorite=true&labelId=l1&labelId=l2"
        "&type=video&resolution=4k&sort=oldest",
        f"{API}/assets",
    ]


def test_reads_each_assets_preview_or_null_until_its_made(make_client: MakeClient) -> None:
    video = preview("a1", clip=True)
    still = preview("a3")
    zerogen, _ = make_client(
        json_response(
            page(
                asset("a1", type="video", mimeType="video/mp4", preview=video),
                asset("a2", type="audio", mimeType="audio/mpeg", width=None, height=None),
            )
        ),
        json_response(asset("a3", prompt="A lighthouse", promptTruncated=False, preview=still)),
    )
    clip, sound = first_page(zerogen.assets.search(project_id="p1")).data
    assert clip.preview is not None
    assert clip.preview.image96_url == video["image96Url"]
    assert clip.preview.image512_url == video["image512Url"]
    assert clip.preview.video_url == video["videoUrl"]
    assert clip.preview.expires_at == datetime(2026, 10, 25, 0, 5, tzinfo=timezone.utc)
    assert sound.preview is None
    detail = run(zerogen.assets.get("a3"))
    assert detail.preview is not None
    assert detail.preview.image512_url == still["image512Url"]
    assert detail.preview.video_url is None


def test_downloads_from_storage_without_the_api_key_or_any_of_the_clients_headers(
    make_client: MakeClient,
) -> None:
    zerogen, calls = make_client(
        json_response(download_link(SIGNED)),
        httpx.Response(200, content=HELLO),
        default_headers={"X-Team": "t1"},
        http_options={"headers": {"X-Proxy-Tag": "p1"}},
    )
    assert run(zerogen.assets.download("a1", headers={"X-Trace": "r1"})) == HELLO
    api, storage = calls
    assert api.url == f"{API}/assets/a1/download"
    assert api.headers["authorization"] == "Bearer zg_test_key"
    assert (api.headers["x-team"], api.headers["x-trace"]) == ("t1", "r1")
    assert (storage.method, storage.url) == ("GET", SIGNED)
    assert dict(storage.headers) == {"host": "storage.example.com"}
    assert storage.timeout["read"] == 120


def test_doesnt_follow_a_storage_redirect_with_the_clients_cookies(make_client: MakeClient) -> None:
    zerogen, calls = make_client(
        json_response(download_link(SIGNED)),
        httpx.Response(302, headers={"Location": "https://elsewhere.example.com/a1.png"}),
        http_options={"follow_redirects": True, "cookies": {"session": "s1"}},
    )
    error = raises(ZeroGenError, lambda: zerogen.assets.download("a1"))
    assert error.status == 302
    assert [call.url for call in calls] == [f"{API}/assets/a1/download", SIGNED]
    assert "cookie" not in calls[1].headers


def test_streams_each_download_into_a_path_or_a_file_from_a_new_link(
    make_client: MakeClient, tmp_path: Path
) -> None:
    zerogen, calls = make_client(
        json_response(download_link(SIGNED)),
        httpx.Response(200, content=HELLO),
        json_response(download_link(RESIGNED)),
        httpx.Response(200, content=HELLO),
    )
    path = tmp_path / "lighthouse.png"
    run(zerogen.assets.download("a1", path))
    file = io.BytesIO()
    run(zerogen.assets.download("a1", file))
    assert path.read_bytes() == HELLO
    assert file.getvalue() == HELLO
    assert [call.url for call in calls] == [
        f"{API}/assets/a1/download",
        SIGNED,
        f"{API}/assets/a1/download",
        RESIGNED,
    ]


def test_reads_a_new_link_once_when_storage_refuses_an_expired_one(
    make_client: MakeClient,
) -> None:
    zerogen, calls = make_client(
        json_response(download_link(SIGNED)),
        httpx.Response(403, text=EXPIRED),
        json_response(download_link(RESIGNED)),
        httpx.Response(200, content=HELLO),
    )
    assert run(zerogen.assets.download("a1")) == HELLO
    assert [call.url for call in calls][1::2] == [SIGNED, RESIGNED]


def test_reports_storage_refusing_the_new_link_too_without_the_link(
    make_client: MakeClient,
) -> None:
    zerogen, calls = make_client(
        json_response(download_link(SIGNED)),
        httpx.Response(403, text=EXPIRED),
        json_response(download_link(RESIGNED)),
        httpx.Response(403, text=EXPIRED),
    )
    error = raises(ZeroGenError, lambda: zerogen.assets.download("a1"))
    assert (error.status, error.code) == (403, "unexpected_response")
    assert "Signature" not in f"{error} {error.args}"
    assert len(calls) == 4


@pytest.mark.usefixtures("no_backoff")
def test_reports_a_storage_connection_error_without_the_link(make_client: MakeClient) -> None:
    zerogen, _ = make_client(
        json_response(download_link(SIGNED)),
        httpx.ConnectError("Connection refused"),
        max_retries=0,
    )
    error = raises(ZeroGenConnectionError, lambda: zerogen.assets.download("a1"))
    assert "Signature" not in f"{error} {error.args}"


def test_removes_a_partial_file_when_the_download_stops(
    make_client: MakeClient, tmp_path: Path
) -> None:
    zerogen, _ = make_client(
        json_response(download_link(SIGNED)), httpx.Response(200, stream=Broken())
    )
    path = tmp_path / "lighthouse.png"
    error = raises(ZeroGenConnectionError, lambda: zerogen.assets.download("a1", path))
    assert str(error) == "The download stopped before it finished."
    assert not path.exists()


@pytest.mark.usefixtures("no_backoff")
def test_closes_a_storage_error_whose_body_stops(make_client: MakeClient) -> None:
    body = Broken()
    zerogen, _ = make_client(
        json_response(download_link(SIGNED)), httpx.Response(500, stream=body), max_retries=0
    )
    raises(ZeroGenConnectionError, lambda: zerogen.assets.download("a1"))
    assert body.closed


def test_keeps_an_existing_file_it_cant_open(
    make_client: MakeClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(*args: object, **kwargs: object) -> NoReturn:
        raise PermissionError("The file is read-only.")

    async def refuse_async(*args: object, **kwargs: object) -> NoReturn:
        refuse()

    monkeypatch.setattr(assets_module, "open", refuse, raising=False)
    monkeypatch.setattr(anyio, "open_file", refuse_async)
    zerogen, _ = make_client(
        json_response(download_link(SIGNED)), httpx.Response(200, content=HELLO)
    )
    path = tmp_path / "lighthouse.png"
    path.write_bytes(b"original")
    raises(PermissionError, lambda: zerogen.assets.download("a1", path))
    assert path.read_bytes() == b"original"


def test_keeps_the_signature_out_of_httpxs_request_log(
    make_client: MakeClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="httpx")
    zerogen, _ = make_client(
        json_response(download_link(SIGNED)), httpx.Response(200, content=HELLO)
    )
    run(zerogen.assets.download("a1"))
    lines = [record.getMessage() for record in caplog.records if record.name == "httpx"]
    assert len(lines) == 2
    assert f"GET {API}/assets/a1/download " in lines[0]
    assert 'GET https://storage.example.com/a1.png "HTTP/1.1 200 OK"' in lines[1]
