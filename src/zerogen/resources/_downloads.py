"""Downloads from signed storage links, which `assets` and `runs` read in their own ways."""

from __future__ import annotations

import contextlib
import mimetypes
import os
import re
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from dataclasses import dataclass, field
from typing import IO, TYPE_CHECKING, TypeAlias, Union

import anyio
import httpx

from .._errors import ZeroGenConnectionError, ZeroGenError
from .._options import RequestOptions
from ..types import AssetDownload

if TYPE_CHECKING:
    from .._client import AsyncZeroGen, ZeroGen

DownloadDestination: TypeAlias = Union[str, "os.PathLike[str]", IO[bytes]]
"""Where to write a download: a path, or a binary file object open for writing."""

_UNSAFE_CHARACTERS = re.compile(r'[\x00-\x1f\x7f<>:"/\\|?*]')
_DEVICE_NAME = re.compile(
    r"(?i)(con|prn|aux|nul|conin\$|conout\$|com[0-9¹²³]|lpt[0-9¹²³]) *(\..*)?"
)
_MAX_NAME_BYTES = 240
"""Under the 255 bytes most file systems allow, to leave room for a number."""
_MAX_EXTENSION_BYTES = 16
_MAX_NUMBER = 10_000
_STOPPED = "The download stopped before it finished."


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


def _open(
    client: ZeroGen, read_link: Callable[[], AssetDownload], options: RequestOptions
) -> tuple[httpx.Response, AssetDownload]:
    """Reads a new link and opens it in storage, without the API key or any of the client's
    headers. When storage refuses the link as expired, it reads a new one once."""
    refreshed = False
    while True:
        link = read_link()
        try:
            response = client._storage(
                "GET",
                link.url,
                headers={},
                content=lambda: None,
                timeout=options.get("timeout", client.timeout),
                max_retries=options.get("max_retries", client.max_retries),
                stream=True,
            )
        except ZeroGenError as error:
            if error.status != 403 or refreshed:
                raise
            refreshed = True
        else:
            return response, link


async def _async_open(
    client: AsyncZeroGen,
    read_link: Callable[[], Awaitable[AssetDownload]],
    options: RequestOptions,
) -> tuple[httpx.Response, AssetDownload]:
    refreshed = False
    while True:
        link = await read_link()
        try:
            response = await client._storage(
                "GET",
                link.url,
                headers={},
                content=lambda: None,
                timeout=options.get("timeout", client.timeout),
                max_retries=options.get("max_retries", client.max_retries),
                stream=True,
            )
        except ZeroGenError as error:
            if error.status != 403 or refreshed:
                raise
            refreshed = True
        else:
            return response, link


def download(
    client: ZeroGen,
    read_link: Callable[[], AssetDownload],
    destination: DownloadDestination | None,
    options: RequestOptions,
) -> Download | DownloadInfo:
    response, link = _open(client, read_link, options)
    try:
        if destination is None:
            content = b"".join(response.iter_bytes())
            return Download(link.asset_id, link.filename, link.mime_type, len(content), content)
        return _info(link, _write(response.iter_bytes(), destination))
    except httpx.TransportError as error:
        raise ZeroGenConnectionError(_STOPPED) from error
    finally:
        response.close()


def download_to(
    client: ZeroGen,
    read_link: Callable[[], AssetDownload],
    directory: str | os.PathLike[str],
    options: RequestOptions,
) -> SavedDownload:
    response, link = _open(client, read_link, options)
    try:
        name = _safe_name(link.filename, link.asset_id, link.mime_type)
        path, file = _create(directory, name)
        with file:
            size = _fill(file, path, response.iter_bytes())
        return SavedDownload(link.asset_id, link.filename, link.mime_type, size, path)
    except httpx.TransportError as error:
        raise ZeroGenConnectionError(_STOPPED) from error
    finally:
        response.close()


async def async_download(
    client: AsyncZeroGen,
    read_link: Callable[[], Awaitable[AssetDownload]],
    destination: DownloadDestination | None,
    options: RequestOptions,
) -> Download | DownloadInfo:
    response, link = await _async_open(client, read_link, options)
    try:
        if destination is None:
            content = b"".join([chunk async for chunk in response.aiter_bytes()])
            return Download(link.asset_id, link.filename, link.mime_type, len(content), content)
        return _info(link, await _async_write(response.aiter_bytes(), destination))
    except httpx.TransportError as error:
        raise ZeroGenConnectionError(_STOPPED) from error
    finally:
        await response.aclose()


async def async_download_to(
    client: AsyncZeroGen,
    read_link: Callable[[], Awaitable[AssetDownload]],
    directory: str | os.PathLike[str],
    options: RequestOptions,
) -> SavedDownload:
    response, link = await _async_open(client, read_link, options)
    try:
        name = _safe_name(link.filename, link.asset_id, link.mime_type)
        path, file = await _async_create(directory, name)
        async with file:
            size = await _async_fill(file, path, response.aiter_bytes())
        return SavedDownload(link.asset_id, link.filename, link.mime_type, size, path)
    except httpx.TransportError as error:
        raise ZeroGenConnectionError(_STOPPED) from error
    finally:
        await response.aclose()
