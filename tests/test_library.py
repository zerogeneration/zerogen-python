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
    CREATOR,
    DECLARATION,
    FOLDER,
    LABEL,
    WORKFLOW,
    Client,
    api_error,
    asset,
    collect,
    declared,
    download_link,
    first_page,
    json_response,
    page,
    preview,
    raises,
    run,
)

from zerogen import DownloadInfo, SavedDownload, ZeroGenConnectionError, ZeroGenError
from zerogen.resources import _downloads as downloads_module

API = "https://api.zerogen.com/v1"
SIGNED = "https://storage.example.com/a1.png?X-Amz-Expires=300&X-Amz-Signature=first"
RESIGNED = "https://storage.example.com/a1.png?X-Amz-Expires=300&X-Amz-Signature=second"
EXPIRED = "<Error><Code>AccessDenied</Code><Message>Request has expired</Message></Error>"
HELLO = b"hello"
BATCH_CHANGE = {"updatedAssetIds": ["a1"], "skippedAssetIds": ["a2"]}
FOLDER_DELETE = {"folderId": "f1", "eventId": "e1", "undoUntil": "2026-10-25T01:00:00.000Z"}
PROJECT = {
    "id": "p1",
    "name": "Lighthouse",
    "slug": "lighthouse",
    "default": True,
    "apiSandbox": False,
    "createdAt": "2026-10-25T00:00:00.000Z",
}
DETAIL = asset(prompt="A lighthouse", promptTruncated=False)
NAMING_PRESET: dict[str, Any] = {"id": "n1", "projectId": "p1", "name": "Plates", "definition": {}}
PRESET_DEFINITION: Any = {
    "delimiter": "_",
    "fields": [
        {
            "id": "plate",
            "kind": "text",
            "label": "Plate",
            "prefix": "",
            "padding": 1,
            "step": 1,
            "sequence": "number",
            "artistFormat": "initials",
            "dateFormat": "YYYY-MM-DD",
            "defaultValue": "",
        }
    ],
}
ATTACHMENT_DETAIL = {
    "title": "Direction",
    "body": "Warm light.",
    "parent": {"kind": "project", "id": "p1", "name": "Lighthouse"},
    "version": 2,
    "latestVersion": 2,
    "savedAt": "2026-10-25T00:00:00.000Z",
    "savedBy": "u1",
}
ROUTES: list[tuple[Callable[[Client], object], str, Any, dict[str, Any]]] = [
    (lambda z: z.projects.get("p1"), "GET /projects/p1", None, PROJECT),
    (
        lambda z: z.assets.get("a1"),
        "GET /assets/a1",
        None,
        asset(prompt="A lighthouse", promptTruncated=False),
    ),
    (
        lambda z: z.assets.get("a1", include_workflow=True),
        "GET /assets/a1?includeWorkflow=true",
        None,
        asset(prompt="A lighthouse", promptTruncated=False, workflow={"nodes": []}),
    ),
    (
        lambda z: z.assets.declare("a1", DECLARATION),
        "POST /assets/a1/declaration",
        DECLARATION,
        {"assetId": "a1", "runId": "g9", "asset": asset(runId="g9", declared=declared())},
    ),
    (lambda z: z.assets.get_download("a1"), "GET /assets/a1/download", None, download_link(SIGNED)),
    (
        lambda z: z.assets.update("a1", {"favorite": True}),
        "PATCH /assets/a1",
        {"favorite": True},
        {**DETAIL, "favorite": True},
    ),
    (
        lambda z: z.assets.delete("a1"),
        "DELETE /assets/a1",
        None,
        {"assetId": "a1", "projectId": "p1", "deletedAt": "2026-10-25T00:00:00.000Z"},
    ),
    (lambda z: z.assets.restore("a1"), "POST /assets/a1/restore", None, DETAIL),
    (lambda z: z.folders.get("f1"), "GET /folders/f1", None, FOLDER),
    (
        lambda z: z.folders.create({"projectId": "p1", "name": "Shots"}),
        "POST /folders",
        {"projectId": "p1", "name": "Shots"},
        FOLDER,
    ),
    (
        lambda z: z.folders.update("f1", {"parentId": None}),
        "PATCH /folders/f1",
        {"parentId": None},
        FOLDER,
    ),
    (
        lambda z: z.folders.add_assets("f1", {"assetIds": ["a1", "a2"]}),
        "POST /folders/f1/assets",
        {"assetIds": ["a1", "a2"]},
        BATCH_CHANGE,
    ),
    (
        lambda z: z.folders.move_assets("f1", {"assetIds": ["a1"], "fromFolderId": "f0"}),
        "POST /folders/f1/assets/move",
        {"assetIds": ["a1"], "fromFolderId": "f0"},
        BATCH_CHANGE,
    ),
    (
        lambda z: z.folders.remove_assets("f1", {"assetIds": ["a1"]}),
        "POST /folders/f1/assets/remove",
        {"assetIds": ["a1"]},
        BATCH_CHANGE,
    ),
    (
        lambda z: z.folders.delete("f1", assets="keep"),
        "DELETE /folders/f1?assets=keep",
        None,
        FOLDER_DELETE,
    ),
    (
        lambda z: z.folders.restore({"eventId": "e1"}),
        "POST /folders/restore",
        {"eventId": "e1"},
        {"rootId": "f1", "parentId": None},
    ),
    (lambda z: z.labels.get("l1"), "GET /labels/l1", None, LABEL),
    (lambda z: z.labels.create({"name": "Hero"}), "POST /labels", {"name": "Hero"}, LABEL),
    (
        lambda z: z.labels.update("l1", {"color": "#22c55e"}),
        "PATCH /labels/l1",
        {"color": "#22c55e"},
        LABEL,
    ),
    (lambda z: z.labels.archive("l1"), "POST /labels/l1/archive", None, LABEL),
    (lambda z: z.labels.restore("l1"), "POST /labels/l1/restore", None, LABEL),
    (
        lambda z: z.labels.add_assets("l1", {"assetIds": ["a1", "a2"]}),
        "POST /labels/l1/assets",
        {"assetIds": ["a1", "a2"]},
        BATCH_CHANGE,
    ),
    (
        lambda z: z.labels.remove_assets("l1", {"assetIds": ["a1"]}),
        "POST /labels/l1/assets/remove",
        {"assetIds": ["a1"]},
        BATCH_CHANGE,
    ),
    (
        lambda z: z.naming_presets.create(
            {"projectId": "p1", "name": "Plates", "definition": PRESET_DEFINITION}
        ),
        "POST /naming-presets",
        {"projectId": "p1", "name": "Plates", "definition": PRESET_DEFINITION},
        NAMING_PRESET,
    ),
    (
        lambda z: z.skills.get("s1", project_id="p1"),
        "GET /skills/s1?projectId=p1",
        None,
        {"id": "s1", "version": 2, "name": "Storyboards", "description": "Boards", "body": "Draw"},
    ),
    (lambda z: z.attachments.get("t1"), "GET /attachments/t1", None, ATTACHMENT_DETAIL),
    (
        lambda z: z.attachments.get("t1", version=1),
        "GET /attachments/t1?version=1",
        None,
        {**ATTACHMENT_DETAIL, "version": 1},
    ),
    (
        lambda z: z.attachments.create({"projectId": "p1", "title": "Direction", "body": "Warm"}),
        "POST /attachments",
        {"projectId": "p1", "title": "Direction", "body": "Warm"},
        {"projectId": "p1", "version": 1, "attachmentId": "t1", "outcome": "created"},
    ),
    (
        lambda z: z.attachments.revise("t1", {"expectedVersion": 1, "body": "Cool"}),
        "PATCH /attachments/t1",
        {"expectedVersion": 1, "body": "Cool"},
        {"projectId": "p1", "version": 2, "outcome": "revised"},
    ),
    (
        lambda z: z.attachments.delete("t1", expected_version=2),
        "DELETE /attachments/t1?expectedVersion=2",
        None,
        {"projectId": "p1", "version": 3, "outcome": "deleted"},
    ),
    (
        lambda z: z.attachments.restore("t1", {"version": 1, "expectedVersion": 3}),
        "POST /attachments/t1/restore",
        {"version": 1, "expectedVersion": 3},
        {"projectId": "p1", "version": 4, "restoredFrom": 1, "outcome": "restored"},
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
    assert ("idempotency-key" in calls[0].headers) == (method in ("POST", "PATCH", "DELETE"))


def test_reads_what_a_batch_changed_and_skipped(make_client: MakeClient) -> None:
    zerogen, _ = make_client(json_response(BATCH_CHANGE), json_response(BATCH_CHANGE))
    for change in (
        run(zerogen.folders.add_assets("f1", {"assetIds": ["a1", "a2"]})),
        run(zerogen.labels.add_assets("l1", {"assetIds": ["a1", "a2"]})),
    ):
        assert (change.updated_asset_ids, change.skipped_asset_ids) == (["a1"], ["a2"])


@pytest.mark.usefixtures("no_backoff")
def test_retries_a_patch_with_the_same_idempotency_key(make_client: MakeClient) -> None:
    zerogen, calls = make_client(
        api_error(503, "unavailable", retryable=True),
        json_response({**DETAIL, "name": "Hero shot"}),
        json_response(LABEL),
    )
    updated = run(zerogen.assets.update("a1", {"name": "Hero shot"}))
    assert updated.name == "Hero shot"
    first, retry = (call.headers["idempotency-key"] for call in calls[:2])
    assert first == retry
    run(zerogen.labels.update("l1", {"name": "Hero"}, idempotency_key="label-1"))
    assert calls[2].headers["idempotency-key"] == "label-1"


def test_ensure_path_finds_or_creates_each_folder_in_turn(make_client: MakeClient) -> None:
    zerogen, calls = make_client(
        json_response(FOLDER), json_response({**FOLDER, "id": "f2", "parentId": "f1"}, 201)
    )
    folder = run(zerogen.folders.ensure_path("p1", "/Shots//anim/"))
    assert (folder.id, folder.parent_id) == ("f2", "f1")
    assert [call.json() for call in calls] == [
        {"projectId": "p1", "name": "Shots", "parentId": None, "reuseExisting": True},
        {"projectId": "p1", "name": "anim", "parentId": "f1", "reuseExisting": True},
    ]
    assert {call.url for call in calls} == {f"{API}/folders"}
    assert len({call.headers["idempotency-key"] for call in calls}) == 2


def test_ensure_path_takes_names_that_contain_a_slash_as_a_list(make_client: MakeClient) -> None:
    zerogen, calls = make_client(json_response({**FOLDER, "id": "f2", "parentId": "f0"}))
    run(zerogen.folders.ensure_path("p1", ["2026/11/01"], parent_id="f0"))
    assert calls[0].json() == {
        "projectId": "p1",
        "name": "2026/11/01",
        "parentId": "f0",
        "reuseExisting": True,
    }


@pytest.mark.parametrize("path", ["", "/", []])
def test_ensure_path_needs_a_folder_name(make_client: MakeClient, path: str | list[str]) -> None:
    zerogen, calls = make_client()
    raises(ValueError, lambda: zerogen.folders.ensure_path("p1", path))
    assert calls == []


def test_lists_library_collections_with_their_filters(make_client: MakeClient) -> None:
    zerogen, calls = make_client(*[json_response(page()) for _ in range(13)])
    first_page(zerogen.projects.list(limit=2))
    first_page(zerogen.folders.list("p1", limit=100))
    first_page(zerogen.naming_presets.list("p1", cursor="c1"))
    first_page(zerogen.skills.list(project_id="p1"))
    first_page(zerogen.labels.list(include_archived=True))
    first_page(zerogen.labels.list(include_archived=False, limit=5))
    first_page(zerogen.assets.folders("a1", limit=10))
    first_page(zerogen.assets.sources("a1"))
    first_page(zerogen.assets.uses("a1", cursor="c2"))
    first_page(zerogen.luts.list(limit=20))
    first_page(zerogen.attachments.list("p1"))
    first_page(zerogen.attachments.list("p1", folder_id="f1", limit=10))
    first_page(zerogen.attachments.versions("t1", cursor="c3"))
    assert [call.url for call in calls] == [
        f"{API}/projects?limit=2",
        f"{API}/folders?projectId=p1&limit=100",
        f"{API}/naming-presets?projectId=p1&cursor=c1",
        f"{API}/skills?projectId=p1",
        f"{API}/labels?includeArchived=true",
        f"{API}/labels?includeArchived=false&limit=5",
        f"{API}/assets/a1/folders?limit=10",
        f"{API}/assets/a1/sources",
        f"{API}/assets/a1/uses?cursor=c2",
        f"{API}/luts?limit=20",
        f"{API}/attachments?projectId=p1",
        f"{API}/attachments?projectId=p1&folderId=f1&limit=10",
        f"{API}/attachments/t1/versions?cursor=c3",
    ]


def test_pages_through_every_project(make_client: MakeClient) -> None:
    zerogen, calls = make_client(
        json_response(page(PROJECT, next_cursor="c2")),
        json_response(page({**PROJECT, "id": "p2", "default": False})),
    )
    assert [project.id for project in collect(zerogen.projects.list())] == ["p1", "p2"]
    assert [call.url for call in calls] == [f"{API}/projects", f"{API}/projects?cursor=c2"]


def test_rebuilds_an_assets_lineage_from_its_pages_of_sources(make_client: MakeClient) -> None:
    def source(asset_id: str, depth: int, made: str) -> dict[str, Any]:
        edge = {"assetId": made, "sourceAssetId": asset_id, "role": "reference", "kind": "image"}
        return {
            "assetId": asset_id,
            "depth": depth,
            "found": True,
            "deleted": False,
            "name": asset_id,
            "origin": "upload",
            "mimeType": "image/png",
            "runId": None,
            "prompt": None,
            "edges": [{**edge, "declared": True}],
        }

    zerogen, calls = make_client(
        json_response(page(source("a0", 1, "a1"), next_cursor="c2")),
        json_response(page(source("a00", 2, "a0"))),
    )
    sources = collect(zerogen.assets.sources("a1", limit=1))
    assert [(edge.source_asset_id, edge.asset_id) for s in sources for edge in s.edges] == [
        ("a0", "a1"),
        ("a00", "a0"),
    ]
    assert sources[0].edges[0].declared
    assert calls[1].url == f"{API}/assets/a1/sources?limit=1&cursor=c2"


def test_reads_an_assets_folders_and_the_luts_to_grade_it_with(make_client: MakeClient) -> None:
    lut = {
        "id": "lut1",
        "name": "Film",
        "size": 33,
        "inputColor": "slog3-sgamut3cine",
        "createdAt": "2026-10-25T00:00:00.000Z",
    }
    zerogen, _ = make_client(
        json_response(page({"folderId": "f1", "path": "Shots/SH010"})),
        json_response(page(lut, {**lut, "id": "lut2", "inputColor": "future-log"})),
    )
    (folder,) = first_page(zerogen.assets.folders("a1")).data
    assert (folder.folder_id, folder.path) == ("f1", "Shots/SH010")
    film, future = first_page(zerogen.luts.list()).data
    assert (film.id, film.input_color, future.input_color) == (
        "lut1",
        "slog3-sgamut3cine",
        "future-log",
    )


def test_reads_attachment_ids_as_strings_and_a_stale_revision_as_a_conflict(
    make_client: MakeClient,
) -> None:
    listed = {
        "attachmentId": "7c1d2e3f-4a5b-4c6d-8e9f-0a1b2c3d4e5f",
        "title": "Direction",
        "parent": {"kind": "clip", "id": "c1", "name": "SH010"},
        "version": 2,
        "characters": 11,
        "updatedAt": "2026-10-25T00:00:00.000Z",
        "updatedBy": "u1",
    }
    zerogen, _ = make_client(
        json_response(page(listed)),
        api_error(409, "version_conflict", param="expectedVersion", details={"currentVersion": 3}),
    )
    (attachment,) = first_page(zerogen.attachments.list("p1")).data
    assert attachment.attachment_id == listed["attachmentId"]
    assert attachment.parent.kind == "clip"
    error = raises(
        ZeroGenError,
        lambda: zerogen.attachments.revise(
            attachment.attachment_id, {"expectedVersion": 2, "body": "Cool"}
        ),
    )
    assert (error.status, error.code, error.param) == (409, "version_conflict", "expectedVersion")
    assert error.details == {"currentVersion": 3}
    assert error.reason is None


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


def test_finds_who_made_an_asset_and_where_to_open_it(make_client: MakeClient) -> None:
    url = "https://acme.zerogen.com/library/a1"
    zerogen, calls = make_client(
        json_response(
            page(
                asset("a1", createdVia="mcp", webUrl=url),
                asset("a2", createdBy=None, createdVia=None),
            )
        ),
        json_response(asset("a1", prompt="A lighthouse", promptTruncated=False, webUrl=url)),
    )
    made, unknown = first_page(zerogen.assets.search(created_by=["u1", "u2"])).data
    assert calls[0].url == f"{API}/assets?createdBy=u1&createdBy=u2"
    assert made.created_by is not None
    assert (made.created_by.id, made.created_by.name) == ("u1", CREATOR["name"])
    assert (made.created_via, made.web_url) == ("mcp", url)
    assert (unknown.created_by, unknown.created_via, unknown.web_url) == (None, None, None)
    detail = run(zerogen.assets.get("a1"))
    assert detail.created_by is not None
    assert (detail.created_by.id, detail.web_url) == ("u1", url)


@pytest.mark.usefixtures("no_backoff")
def test_retries_a_folder_deletion_with_the_same_idempotency_key_and_can_undo_it(
    make_client: MakeClient,
) -> None:
    zerogen, calls = make_client(
        api_error(503, "unavailable", retryable=True),
        json_response(FOLDER_DELETE),
        json_response(FOLDER_DELETE),
        json_response({"rootId": "f1", "parentId": "f0"}),
    )
    deleted = run(zerogen.folders.delete("f1", assets="trash"))
    assert [call.url for call in calls] == [f"{API}/folders/f1?assets=trash"] * 2
    first, retry = (call.headers["idempotency-key"] for call in calls)
    assert first == retry
    assert len(first) == 36
    run(zerogen.folders.delete("f1", assets="keep", idempotency_key="job-1"))
    assert calls[2].headers["idempotency-key"] == "job-1"
    assert (deleted.folder_id, deleted.event_id) == ("f1", "e1")
    assert deleted.undo_until == datetime(2026, 10, 25, 1, tzinfo=timezone.utc)
    restored = run(zerogen.folders.restore({"eventId": deleted.event_id}))
    assert (restored.root_id, restored.parent_id) == ("f1", "f0")
    assert calls[3].json() == {"eventId": "e1"}


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
    assert detail.declared is None


def test_reads_what_an_upload_declared_and_its_workflow_when_asked(
    make_client: MakeClient,
) -> None:
    detail = asset(
        origin="upload",
        runId="g9",
        prompt="A lighthouse at dawn",
        promptTruncated=False,
        declared=declared(),
        workflow=WORKFLOW,
    )
    zerogen, calls = make_client(json_response(detail))
    read = run(zerogen.assets.get("a1", include_workflow=True))
    assert read.declared is not None
    assert read.declared.tool.name == "comfyui"
    assert read.declared.tool.integration is not None
    assert read.declared.tool.integration.name == "zerogen-nodes"
    assert read.declared.external_ref is not None
    assert read.declared.external_ref.id == "prompt-1"
    assert read.declared.occurred_at == datetime(2026, 10, 25, tzinfo=timezone.utc)
    assert read.workflow == WORKFLOW
    assert calls[0].url == f"{API}/assets/a1?includeWorkflow=true"


def test_downloads_from_storage_without_the_api_key_or_any_of_the_clients_headers(
    make_client: MakeClient,
) -> None:
    zerogen, calls = make_client(
        json_response(download_link(SIGNED)),
        httpx.Response(200, content=HELLO),
        default_headers={"X-Team": "t1"},
        http_options={"headers": {"X-Proxy-Tag": "p1"}},
    )
    download = run(zerogen.assets.download("a1", headers={"X-Trace": "r1"}))
    assert download.content == HELLO
    assert (download.asset_id, download.filename) == ("a1", "lighthouse.png")
    assert (download.mime_type, download.size_bytes) == ("image/png", 5)
    assert "content" not in repr(download)
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
    file = io.BytesIO()
    info = DownloadInfo("a1", "lighthouse.png", "image/png", 5)
    assert run(zerogen.assets.download("a1", path)) == info
    assert run(zerogen.assets.download("a1", file)) == info
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
    assert run(zerogen.assets.download("a1")).content == HELLO
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


def test_quotes_only_the_storage_errors_code_and_message(make_client: MakeClient) -> None:
    echo = (
        "<Error><Code>SignatureDoesNotMatch</Code><Message>The signature does not match"
        "</Message><StringToSign>AWS4-HMAC-SHA256 X-Amz-Credential=AKIDEXAMPLE</StringToSign>"
        "<CanonicalRequest>GET /a1.png X-Amz-Signature=first</CanonicalRequest></Error>"
    )
    zerogen, _ = make_client(
        json_response(download_link(SIGNED)),
        httpx.Response(400, text=echo),
    )
    error = raises(ZeroGenError, lambda: zerogen.assets.download("a1"))
    assert str(error) == (
        "unexpected_response: Storage answered HTTP 400: SignatureDoesNotMatch: "
        "The signature does not match"
    )
    assert error.details is None
    for secret in ("AKIDEXAMPLE", "X-Amz-Signature", "StringToSign"):
        assert secret not in f"{error} {error.args}"


@pytest.mark.usefixtures("no_backoff")
def test_quotes_nothing_from_a_storage_error_that_isnt_s3s(make_client: MakeClient) -> None:
    zerogen, _ = make_client(
        json_response(download_link(SIGNED)),
        httpx.Response(500, text=f"proxy failed fetching {SIGNED}"),
        max_retries=0,
    )
    error = raises(ZeroGenError, lambda: zerogen.assets.download("a1"))
    assert (str(error), error.retryable) == (
        "unexpected_response: Storage answered HTTP 500",
        True,
    )


def test_downloads_a_run_output_with_only_its_runs_link(
    make_client: MakeClient, tmp_path: Path
) -> None:
    zerogen, calls = make_client(
        json_response(download_link(SIGNED)),
        httpx.Response(200, content=HELLO),
        json_response(download_link(RESIGNED)),
        httpx.Response(403, text=EXPIRED),
        json_response(download_link(SIGNED)),
        httpx.Response(200, content=HELLO),
        json_response(download_link(RESIGNED)),
        httpx.Response(200, content=HELLO),
    )
    output = run(zerogen.runs.download_output("g1", "a1"))
    assert (output.content, output.filename) == (HELLO, "lighthouse.png")
    saved = run(zerogen.runs.download_output_to("g1", "a1", tmp_path))
    assert Path(saved.path).read_bytes() == HELLO
    file = io.BytesIO()
    info = run(zerogen.runs.download_output("g1", "a1", file))
    assert (info, file.getvalue()) == (DownloadInfo("a1", "lighthouse.png", "image/png", 5), HELLO)
    link = f"{API}/runs/g1/outputs/a1/download"
    assert [call.url for call in calls] == [
        link,
        SIGNED,
        link,
        RESIGNED,
        link,
        SIGNED,
        link,
        RESIGNED,
    ]
    assert all("authorization" not in call.headers for call in calls[1::2])


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


def test_saves_into_a_directory_under_a_free_name_without_overwriting(
    make_client: MakeClient, tmp_path: Path
) -> None:
    zerogen, calls = make_client(
        json_response(download_link(SIGNED)),
        httpx.Response(200, content=HELLO),
        json_response(download_link(RESIGNED)),
        httpx.Response(200, content=HELLO),
    )
    (tmp_path / "lighthouse.png").write_bytes(b"original")
    first = run(zerogen.assets.download_to("a1", tmp_path))
    second = run(zerogen.assets.download_to("a1", str(tmp_path)))
    assert first == SavedDownload(
        "a1", "lighthouse.png", "image/png", 5, str(tmp_path / "lighthouse (1).png")
    )
    assert second.path == str(tmp_path / "lighthouse (2).png")
    assert (tmp_path / "lighthouse.png").read_bytes() == b"original"
    assert Path(first.path).read_bytes() == Path(second.path).read_bytes() == HELLO
    assert [call.url for call in calls][1::2] == [SIGNED, RESIGNED]


def test_saves_an_untrusted_filename_inside_the_directory(
    make_client: MakeClient, tmp_path: Path
) -> None:
    link = {**download_link(SIGNED), "filename": "../../outside.png"}
    zerogen, _ = make_client(json_response(link), httpx.Response(200, content=HELLO))
    saved = run(zerogen.assets.download_to("a1", tmp_path))
    assert saved.filename == "../../outside.png"
    assert saved.path == str(tmp_path / "_.._outside.png")
    assert [path.name for path in tmp_path.iterdir()] == ["_.._outside.png"]


def test_removes_a_file_it_saved_into_a_directory_when_the_download_stops(
    make_client: MakeClient, tmp_path: Path
) -> None:
    zerogen, _ = make_client(
        json_response(download_link(SIGNED)), httpx.Response(200, stream=Broken())
    )
    raises(ZeroGenConnectionError, lambda: zerogen.assets.download_to("a1", tmp_path))
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    ("filename", "saved_as"),
    [
        ("lighthouse.png", "lighthouse.png"),
        ("../../etc/passwd", "_.._etc_passwd"),
        ("C:\\Windows\\win.ini", "C__Windows_win.ini"),
        ('a<b>c:d"e|f?g*h.png', "a_b_c_d_e_f_g_h.png"),
        ("tab\tand\x00null.png", "tab_and_null.png"),
        ("  .hidden.png. ", "hidden.png"),
        ("CON.png", "_CON.png"),
        ("lpt1", "_lpt1"),
        ("CON .png", "_CON .png"),
        ("com1  .tar.gz", "_com1  .tar.gz"),
        ("CONOUT$.log", "_CONOUT$.log"),
        ("console.png", "console.png"),
        ("", "a1.png"),
        ("...", "a1.png"),
        ("x" * 300 + ".png", "x" * 236 + ".png"),
        ("é" * 200 + ".png", "é" * 118 + ".png"),
        ("notes." + "y" * 40, "notes." + "y" * 40),
    ],
)
def test_makes_a_safe_name_from_the_files_untrusted_filename(filename: str, saved_as: str) -> None:
    assert downloads_module._safe_name(filename, "a1", "image/png") == saved_as


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

    monkeypatch.setattr(downloads_module, "open", refuse, raising=False)
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
