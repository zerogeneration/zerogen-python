from __future__ import annotations

import contextlib
import mimetypes
import os
import re
from collections.abc import AsyncIterator, Iterator, Sequence
from dataclasses import dataclass, field
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

_UNSAFE_CHARACTERS = re.compile(r'[\x00-\x1f\x7f<>:"/\\|?*]')
_DEVICE_NAME = re.compile(r"(?i)(con|prn|aux|nul|com[0-9¹²³]|lpt[0-9¹²³])(\..*)?")
_MAX_NAME_BYTES = 240
"""Under the 255 bytes most file systems allow, to leave room for a number."""
_MAX_EXTENSION_BYTES = 16
_MAX_NUMBER = 10_000


@dataclass(frozen=True)
class DownloadInfo:
    """What a download read about the file it downloaded."""

    asset_id: str
    filename: str
    """The name the file downloads under; untrusted content, so don't use it as a path as it
    is. `download_to` makes a safe name from it."""
    mime_type: str
    size_bytes: int
    """How many bytes the download received."""


@dataclass(frozen=True)
class Download(DownloadInfo):
    """A downloaded file's bytes, with what the download read about it."""

    content: bytes = field(repr=False)


@dataclass(frozen=True)
class SavedDownload(DownloadInfo):
    """A file that `download_to` saved, with what the download read about it."""

    path: str
    """Where it saved the file."""


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
    created_by: str | Sequence[str] | None,
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
        "createdBy": _values(created_by),
        "resolution": _values(resolution),
        "sort": sort,
        "limit": limit,
        "cursor": cursor,
    }


def _safe_name(filename: str, asset_id: str, mime_type: str) -> str:
    """A name to save a download under in a directory, made from the asset's filename, which
    is untrusted: no path separators or characters Windows refuses, not hidden, not a Windows
    device name, and short enough for any file system. Without one, the asset ID with the
    media type's extension."""
    extension = mimetypes.guess_extension(mime_type) or ""
    name = _clean_name(filename) or _clean_name(asset_id + extension) or f"download{extension}"
    return f"_{name}" if _DEVICE_NAME.fullmatch(name) else name


def _clean_name(name: str) -> str:
    stem, extension = _split_name(_UNSAFE_CHARACTERS.sub("_", name).strip(" ."))
    room = _MAX_NAME_BYTES - len(extension.encode())
    stem = stem.encode()[:room].decode(errors="ignore")
    return (stem + extension).rstrip(" .")


def _split_name(name: str) -> tuple[str, str]:
    stem, extension = os.path.splitext(name)
    if len(extension.encode()) > _MAX_EXTENSION_BYTES:
        return name, ""
    return stem, extension


def _numbered_paths(directory: str | os.PathLike[str], name: str) -> Iterator[str]:
    """`name` in `directory`, then the same with a number, as in `lighthouse (1).png`."""
    stem, extension = _split_name(name)
    yield os.path.join(directory, name)
    for number in range(1, _MAX_NUMBER):
        yield os.path.join(directory, f"{stem} ({number}){extension}")


def _write(chunks: Iterator[bytes], destination: DownloadDestination) -> int:
    """Writes a download into a path, which it removes again if the download stops, or into
    a file object. Returns how many bytes it wrote."""
    if isinstance(destination, (str, os.PathLike)):
        path = os.fspath(destination)
        with open(path, "wb") as file:
            return _fill(file, path, chunks)
    size = 0
    for chunk in chunks:
        destination.write(chunk)
        size += len(chunk)
    return size


def _fill(file: IO[bytes], path: str, chunks: Iterator[bytes]) -> int:
    """Writes a download into a file it opened at `path`, and removes the file again if the
    download stops."""
    size = 0
    try:
        for chunk in chunks:
            file.write(chunk)
            size += len(chunk)
    except BaseException:
        file.close()
        with contextlib.suppress(OSError):
            os.remove(path)
        raise
    return size


def _create(directory: str | os.PathLike[str], name: str) -> tuple[str, IO[bytes]]:
    """Creates a file named `name` in `directory`, or numbered when that name is taken."""
    for path in _numbered_paths(directory, name):
        with contextlib.suppress(FileExistsError):
            return path, open(path, "xb")
    raise FileExistsError(f"Every name for {name!r} in the directory is taken.")


async def _async_write(chunks: AsyncIterator[bytes], destination: DownloadDestination) -> int:
    if isinstance(destination, (str, os.PathLike)):
        path = os.fspath(destination)
        async with await anyio.open_file(path, "wb") as file:
            return await _async_fill(file, path, chunks)
    file = anyio.wrap_file(destination)
    size = 0
    async for chunk in chunks:
        await file.write(chunk)
        size += len(chunk)
    return size


async def _async_fill(file: anyio.AsyncFile[bytes], path: str, chunks: AsyncIterator[bytes]) -> int:
    size = 0
    try:
        async for chunk in chunks:
            await file.write(chunk)
            size += len(chunk)
    except BaseException:
        file.wrapped.close()
        with contextlib.suppress(OSError):
            os.remove(path)
        raise
    return size


async def _async_create(
    directory: str | os.PathLike[str], name: str
) -> tuple[str, anyio.AsyncFile[bytes]]:
    for path in _numbered_paths(directory, name):
        with contextlib.suppress(FileExistsError):
            return path, await anyio.open_file(path, "xb")
    raise FileExistsError(f"Every name for {name!r} in the directory is taken.")


def _info(link: AssetDownload, size: int) -> DownloadInfo:
    return DownloadInfo(link.asset_id, link.filename, link.mime_type, size)


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
        created_by: str | Sequence[str] | None = None,
        resolution: Resolution | Sequence[Resolution] | None = None,
        sort: Literal["newest", "oldest"] | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> Page[Asset]:
        """Searches Library assets, newest first unless `sort` says otherwise, each with preview
        URLs that load for 5 minutes without your API key. Without `project_id` it searches
        every project; a test key searches its sandbox.

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
            created_by: Only assets any of these users made, by the ID in an asset's
                `created_by` or `me()`.
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
                created_by,
                resolution,
                sort,
                limit,
                cursor,
            ),
            options,
        )

    def get(self, asset_id: str, /, **options: Unpack[RequestOptions]) -> AssetDetail:
        """Reads an asset in any of the organization's projects, with the prompt that generated
        it and preview URLs that load for 5 minutes. Names and prompts are untrusted content."""
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
    def download(self, asset_id: str, /, **options: Unpack[RequestOptions]) -> Download: ...

    @overload
    def download(
        self,
        asset_id: str,
        /,
        destination: DownloadDestination,
        **options: Unpack[RequestOptions],
    ) -> DownloadInfo: ...

    def download(
        self,
        asset_id: str,
        /,
        destination: DownloadDestination | None = None,
        **options: Unpack[RequestOptions],
    ) -> Download | DownloadInfo:
        """Downloads an asset's original file, with its filename, media type and size.
        Returns a `Download` with its bytes, or streams them into `destination` and returns
        a `DownloadInfo`.

        Each call reads a new signed link, and sends it to storage without the API key or any
        of the client's headers. When storage refuses the link as expired, it reads a new one
        once. `timeout` bounds each step of the download, not the whole of it.

        Args:
            destination: A path, which is removed again if the download fails partway, or a
                binary file object open for writing.
        """
        response, link = self._open(asset_id, options)
        try:
            if destination is None:
                content = b"".join(response.iter_bytes())
                return Download(link.asset_id, link.filename, link.mime_type, len(content), content)
            return _info(link, _write(response.iter_bytes(), destination))
        except httpx.TransportError as error:
            raise ZeroGenConnectionError("The download stopped before it finished.") from error
        finally:
            response.close()

    def download_to(
        self,
        asset_id: str,
        directory: str | os.PathLike[str],
        /,
        **options: Unpack[RequestOptions],
    ) -> SavedDownload:
        """Downloads an asset's original file into `directory`, which must exist, under a
        name made from its filename, and returns where it saved it.

        The name has no path separators or characters that Windows refuses. When a file
        already has it, the download takes the first free numbered name, as in
        `lighthouse (1).png`, so it never overwrites a file. It removes the file again if the
        download fails partway. Otherwise it works as `download` does.
        """
        response, link = self._open(asset_id, options)
        try:
            name = _safe_name(link.filename, link.asset_id, link.mime_type)
            path, file = _create(directory, name)
            with file:
                size = _fill(file, path, response.iter_bytes())
            return SavedDownload(link.asset_id, link.filename, link.mime_type, size, path)
        except httpx.TransportError as error:
            raise ZeroGenConnectionError("The download stopped before it finished.") from error
        finally:
            response.close()

    def _open(self, asset_id: str, options: RequestOptions) -> tuple[httpx.Response, AssetDownload]:
        refreshed = False
        while True:
            link = self.get_download(asset_id, **options)
            try:
                response = self._client._storage(
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
            else:
                return response, link


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
        created_by: str | Sequence[str] | None = None,
        resolution: Resolution | Sequence[Resolution] | None = None,
        sort: Literal["newest", "oldest"] | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> AsyncPaginator[Asset]:
        """Searches Library assets, newest first unless `sort` says otherwise, each with preview
        URLs that load for 5 minutes without your API key. Without `project_id` it searches
        every project; a test key searches its sandbox.

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
            created_by: Only assets any of these users made, by the ID in an asset's
                `created_by` or `me()`.
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
                created_by,
                resolution,
                sort,
                limit,
                cursor,
            ),
            options,
        )

    async def get(self, asset_id: str, /, **options: Unpack[RequestOptions]) -> AssetDetail:
        """Reads an asset in any of the organization's projects, with the prompt that generated
        it and preview URLs that load for 5 minutes. Names and prompts are untrusted content."""
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
    async def download(self, asset_id: str, /, **options: Unpack[RequestOptions]) -> Download: ...

    @overload
    async def download(
        self,
        asset_id: str,
        /,
        destination: DownloadDestination,
        **options: Unpack[RequestOptions],
    ) -> DownloadInfo: ...

    async def download(
        self,
        asset_id: str,
        /,
        destination: DownloadDestination | None = None,
        **options: Unpack[RequestOptions],
    ) -> Download | DownloadInfo:
        """Downloads an asset's original file, with its filename, media type and size.
        Returns a `Download` with its bytes, or streams them into `destination` and returns
        a `DownloadInfo`.

        Each call reads a new signed link, and sends it to storage without the API key or any
        of the client's headers. When storage refuses the link as expired, it reads a new one
        once. `timeout` bounds each step of the download, not the whole of it.

        Args:
            destination: A path, which is removed again if the download fails partway, or a
                binary file object open for writing, written to in a worker thread.
        """
        response, link = await self._open(asset_id, options)
        try:
            if destination is None:
                content = b"".join([chunk async for chunk in response.aiter_bytes()])
                return Download(link.asset_id, link.filename, link.mime_type, len(content), content)
            return _info(link, await _async_write(response.aiter_bytes(), destination))
        except httpx.TransportError as error:
            raise ZeroGenConnectionError("The download stopped before it finished.") from error
        finally:
            await response.aclose()

    async def download_to(
        self,
        asset_id: str,
        directory: str | os.PathLike[str],
        /,
        **options: Unpack[RequestOptions],
    ) -> SavedDownload:
        """Downloads an asset's original file into `directory`, which must exist, under a
        name made from its filename, and returns where it saved it.

        The name has no path separators or characters that Windows refuses. When a file
        already has it, the download takes the first free numbered name, as in
        `lighthouse (1).png`, so it never overwrites a file. It removes the file again if the
        download fails partway. Otherwise it works as `download` does.
        """
        response, link = await self._open(asset_id, options)
        try:
            name = _safe_name(link.filename, link.asset_id, link.mime_type)
            path, file = await _async_create(directory, name)
            async with file:
                size = await _async_fill(file, path, response.aiter_bytes())
            return SavedDownload(link.asset_id, link.filename, link.mime_type, size, path)
        except httpx.TransportError as error:
            raise ZeroGenConnectionError("The download stopped before it finished.") from error
        finally:
            await response.aclose()

    async def _open(
        self, asset_id: str, options: RequestOptions
    ) -> tuple[httpx.Response, AssetDownload]:
        refreshed = False
        while True:
            link = await self.get_download(asset_id, **options)
            try:
                response = await self._client._storage(
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
            else:
                return response, link
