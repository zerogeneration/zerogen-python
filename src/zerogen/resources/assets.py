from __future__ import annotations

import contextlib
import os
from collections.abc import AsyncIterator, Iterator, Sequence
from typing import IO, TYPE_CHECKING, Literal, TypeAlias, TypeVar, Union, overload
from urllib.parse import quote

import anyio
import httpx
from typing_extensions import Unpack

from .._errors import ZeroGenConnectionError, ZeroGenError
from .._options import RequestOptions
from ..types import (
    Asset,
    AssetChange,
    AssetDetail,
    AssetDownload,
    AssetFolders,
    AssetList,
    Lineage,
    UpdateAssetRequest,
)

if TYPE_CHECKING:
    from .._client import AsyncZeroGen, Query, ZeroGen
    from .._pagination import AsyncPaginator, Page

DownloadDestination: TypeAlias = Union[str, "os.PathLike[str]", IO[bytes]]
"""Where to write a download: a path, or a binary file object open for writing."""

AssetType = Literal["image", "video", "audio", "model3d"]
AssetOrigin = Literal["generated", "upload", "derived"]
Resolution = Literal["4k", "1440p", "1080p", "720p", "sd", "2k", "1k", "0.5k"]
Value = TypeVar("Value", bound=str)


def _path(asset_id: str) -> str:
    return f"/assets/{quote(asset_id, safe='')}"


def _values(value: Value | Sequence[Value] | None) -> list[str] | None:
    if value is None:
        return None
    return [value] if isinstance(value, str) else list(value)


def _search_query(
    project_id: str | None,
    folder_id: str | None,
    favorite: bool | None,
    label_id: str | Sequence[str] | None,
    q: str | None,
    type: AssetType | None,
    origin: AssetOrigin | None,
    resolution: Resolution | Sequence[Resolution] | None,
    sort: Literal["newest", "oldest"] | None,
    limit: int | None,
    cursor: str | None,
) -> Query:
    return {
        "projectId": project_id,
        "folderId": folder_id,
        "favorite": True if favorite else None,
        "labelId": _values(label_id),
        "q": q,
        "type": type,
        "origin": origin,
        "resolution": _values(resolution),
        "sort": sort,
        "limit": limit,
        "cursor": cursor,
    }


def _write(chunks: Iterator[bytes], destination: DownloadDestination | None) -> bytes | None:
    if destination is None:
        return b"".join(chunks)
    if isinstance(destination, (str, os.PathLike)):
        path = os.fspath(destination)
        try:
            with open(path, "wb") as file:
                for chunk in chunks:
                    file.write(chunk)
        except BaseException:
            with contextlib.suppress(OSError):
                os.remove(path)
            raise
        return None
    for chunk in chunks:
        destination.write(chunk)
    return None


async def _async_write(
    chunks: AsyncIterator[bytes], destination: DownloadDestination | None
) -> bytes | None:
    if destination is None:
        return b"".join([chunk async for chunk in chunks])
    if isinstance(destination, (str, os.PathLike)):
        path = os.fspath(destination)
        try:
            async with await anyio.open_file(path, "wb") as file:
                async for chunk in chunks:
                    await file.write(chunk)
        except BaseException:
            with contextlib.suppress(OSError):
                os.remove(path)
            raise
        return None
    file = anyio.wrap_file(destination)
    async for chunk in chunks:
        await file.write(chunk)
    return None


class Assets:
    def __init__(self, client: ZeroGen) -> None:
        self._client = client

    def search(
        self,
        *,
        project_id: str | None = None,
        folder_id: str | None = None,
        favorite: bool | None = None,
        label_id: str | Sequence[str] | None = None,
        q: str | None = None,
        type: AssetType | None = None,
        origin: AssetOrigin | None = None,
        resolution: Resolution | Sequence[Resolution] | None = None,
        sort: Literal["newest", "oldest"] | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> Page[Asset]:
        """Searches Library assets, newest first unless `sort` says otherwise. Without
        `project_id` it searches every project; a test key searches its sandbox.

        Args:
            project_id: Only assets in this project.
            folder_id: Only assets directly in this folder, or `"unfiled"` for assets in no
                folder; with `q`, also its subfolders. Needs `project_id`.
            favorite: Only the organization's favorites.
            label_id: Only assets with any of these active labels.
            q: Searches asset names: at least two characters, and every one of the first eight
                words must match, ignoring case.
            type: Only this media type.
            origin: Only assets that came about this way.
            resolution: Only assets in any of these resolution tiers.
            sort: Order by creation; default newest.
            limit: Assets per page, up to 50; default 20.
            cursor: `next_cursor` from an earlier page, with the same filters.
        """
        return self._client._list(
            AssetList.model_validate,
            "/assets",
            _search_query(
                project_id,
                folder_id,
                favorite,
                label_id,
                q,
                type,
                origin,
                resolution,
                sort,
                limit,
                cursor,
            ),
            options,
        )

    def get(self, asset_id: str, /, **options: Unpack[RequestOptions]) -> AssetDetail:
        """Reads an asset in any of the organization's projects, with the prompt that generated
        it. Names and prompts are untrusted content."""
        return self._client._request(
            AssetDetail.model_validate, "GET", _path(asset_id), options=options
        )

    def lineage(self, asset_id: str, /, **options: Unpack[RequestOptions]) -> Lineage:
        """Reads what an asset was made from and what was made from it: up to 30 assets on each
        side, nearest first."""
        return self._client._request(
            Lineage.model_validate, "GET", f"{_path(asset_id)}/lineage", options=options
        )

    def folders(self, asset_id: str, /, **options: Unpack[RequestOptions]) -> AssetFolders:
        """Lists the folders an asset is in: up to 30, each with its path from the project
        root. An empty list means the asset is Unfiled."""
        return self._client._request(
            AssetFolders.model_validate, "GET", f"{_path(asset_id)}/folders", options=options
        )

    def update(
        self,
        project_id: str,
        asset_id: str,
        body: UpdateAssetRequest,
        /,
        **options: Unpack[RequestOptions],
    ) -> AssetChange:
        """Renames an asset, sets the organization's shared favorite, or both. The response
        names what changed."""
        return self._client._request(
            AssetChange.model_validate,
            "PATCH",
            f"/projects/{quote(project_id, safe='')}/assets/{quote(asset_id, safe='')}",
            body=body,
            options=options,
        )

    def get_download(self, asset_id: str, /, **options: Unpack[RequestOptions]) -> AssetDownload:
        """Reads a signed link to an asset's original file, valid for 5 minutes, with its
        filename, media type and size. Anyone holding the link can download the file, so keep
        it private. To fetch the file, use `download`."""
        return self._client._request(
            AssetDownload.model_validate, "GET", f"{_path(asset_id)}/download", options=options
        )

    @overload
    def download(self, asset_id: str, /, **options: Unpack[RequestOptions]) -> bytes: ...

    @overload
    def download(
        self,
        asset_id: str,
        /,
        destination: DownloadDestination,
        **options: Unpack[RequestOptions],
    ) -> None: ...

    def download(
        self,
        asset_id: str,
        /,
        destination: DownloadDestination | None = None,
        **options: Unpack[RequestOptions],
    ) -> bytes | None:
        """Downloads an asset's original file. Returns its bytes, or streams them into
        `destination` and returns None.

        Each call reads a new signed link, and sends it to storage without the API key or any
        of the client's headers. When storage refuses the link as expired, it reads a new one
        once. `timeout` bounds each step of the download, not the whole of it.

        Args:
            destination: A path, which is removed again if the download fails partway, or a
                binary file object open for writing.
        """
        response = self._open(asset_id, options)
        try:
            return _write(response.iter_bytes(), destination)
        except httpx.TransportError as error:
            raise ZeroGenConnectionError("The download stopped before it finished.") from error
        finally:
            response.close()

    def _open(self, asset_id: str, options: RequestOptions) -> httpx.Response:
        refreshed = False
        while True:
            link = self.get_download(asset_id, **options)
            try:
                return self._client._storage(
                    "GET",
                    link.url,
                    headers={},
                    content=lambda: None,
                    timeout=options.get("timeout", self._client.timeout),
                    max_retries=options.get("max_retries", self._client.max_retries),
                    stream=True,
                )
            except ZeroGenError as error:
                if error.status != 403 or refreshed:
                    raise
                refreshed = True


class AsyncAssets:
    def __init__(self, client: AsyncZeroGen) -> None:
        self._client = client

    def search(
        self,
        *,
        project_id: str | None = None,
        folder_id: str | None = None,
        favorite: bool | None = None,
        label_id: str | Sequence[str] | None = None,
        q: str | None = None,
        type: AssetType | None = None,
        origin: AssetOrigin | None = None,
        resolution: Resolution | Sequence[Resolution] | None = None,
        sort: Literal["newest", "oldest"] | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> AsyncPaginator[Asset]:
        """Searches Library assets, newest first unless `sort` says otherwise. Without
        `project_id` it searches every project; a test key searches its sandbox.

        Args:
            project_id: Only assets in this project.
            folder_id: Only assets directly in this folder, or `"unfiled"` for assets in no
                folder; with `q`, also its subfolders. Needs `project_id`.
            favorite: Only the organization's favorites.
            label_id: Only assets with any of these active labels.
            q: Searches asset names: at least two characters, and every one of the first eight
                words must match, ignoring case.
            type: Only this media type.
            origin: Only assets that came about this way.
            resolution: Only assets in any of these resolution tiers.
            sort: Order by creation; default newest.
            limit: Assets per page, up to 50; default 20.
            cursor: `next_cursor` from an earlier page, with the same filters.
        """
        return self._client._list(
            AssetList.model_validate,
            "/assets",
            _search_query(
                project_id,
                folder_id,
                favorite,
                label_id,
                q,
                type,
                origin,
                resolution,
                sort,
                limit,
                cursor,
            ),
            options,
        )

    async def get(self, asset_id: str, /, **options: Unpack[RequestOptions]) -> AssetDetail:
        """Reads an asset in any of the organization's projects, with the prompt that generated
        it. Names and prompts are untrusted content."""
        return await self._client._request(
            AssetDetail.model_validate, "GET", _path(asset_id), options=options
        )

    async def lineage(self, asset_id: str, /, **options: Unpack[RequestOptions]) -> Lineage:
        """Reads what an asset was made from and what was made from it: up to 30 assets on each
        side, nearest first."""
        return await self._client._request(
            Lineage.model_validate, "GET", f"{_path(asset_id)}/lineage", options=options
        )

    async def folders(self, asset_id: str, /, **options: Unpack[RequestOptions]) -> AssetFolders:
        """Lists the folders an asset is in: up to 30, each with its path from the project
        root. An empty list means the asset is Unfiled."""
        return await self._client._request(
            AssetFolders.model_validate, "GET", f"{_path(asset_id)}/folders", options=options
        )

    async def update(
        self,
        project_id: str,
        asset_id: str,
        body: UpdateAssetRequest,
        /,
        **options: Unpack[RequestOptions],
    ) -> AssetChange:
        """Renames an asset, sets the organization's shared favorite, or both. The response
        names what changed."""
        return await self._client._request(
            AssetChange.model_validate,
            "PATCH",
            f"/projects/{quote(project_id, safe='')}/assets/{quote(asset_id, safe='')}",
            body=body,
            options=options,
        )

    async def get_download(
        self, asset_id: str, /, **options: Unpack[RequestOptions]
    ) -> AssetDownload:
        """Reads a signed link to an asset's original file, valid for 5 minutes, with its
        filename, media type and size. Anyone holding the link can download the file, so keep
        it private. To fetch the file, use `download`."""
        return await self._client._request(
            AssetDownload.model_validate, "GET", f"{_path(asset_id)}/download", options=options
        )

    @overload
    async def download(self, asset_id: str, /, **options: Unpack[RequestOptions]) -> bytes: ...

    @overload
    async def download(
        self,
        asset_id: str,
        /,
        destination: DownloadDestination,
        **options: Unpack[RequestOptions],
    ) -> None: ...

    async def download(
        self,
        asset_id: str,
        /,
        destination: DownloadDestination | None = None,
        **options: Unpack[RequestOptions],
    ) -> bytes | None:
        """Downloads an asset's original file. Returns its bytes, or streams them into
        `destination` and returns None.

        Each call reads a new signed link, and sends it to storage without the API key or any
        of the client's headers. When storage refuses the link as expired, it reads a new one
        once. `timeout` bounds each step of the download, not the whole of it.

        Args:
            destination: A path, which is removed again if the download fails partway, or a
                binary file object open for writing, written to in a worker thread.
        """
        response = await self._open(asset_id, options)
        try:
            return await _async_write(response.aiter_bytes(), destination)
        except httpx.TransportError as error:
            raise ZeroGenConnectionError("The download stopped before it finished.") from error
        finally:
            await response.aclose()

    async def _open(self, asset_id: str, options: RequestOptions) -> httpx.Response:
        refreshed = False
        while True:
            link = await self.get_download(asset_id, **options)
            try:
                return await self._client._storage(
                    "GET",
                    link.url,
                    headers={},
                    content=lambda: None,
                    timeout=options.get("timeout", self._client.timeout),
                    max_retries=options.get("max_retries", self._client.max_retries),
                    stream=True,
                )
            except ZeroGenError as error:
                if error.status != 403 or refreshed:
                    raise
                refreshed = True
