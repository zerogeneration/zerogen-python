from __future__ import annotations

import hashlib
import os
from collections.abc import AsyncIterator, Iterator
from typing import IO, TYPE_CHECKING, Literal, TypeAlias, Union
from urllib.parse import quote

import anyio
import anyio.to_thread
from pydantic import Field
from typing_extensions import Unpack

from .._options import PostRequestOptions, RequestOptions
from ..types import CreateUploadRequest, Upload

if TYPE_CHECKING:
    from .._client import AsyncZeroGen, ZeroGen

UploadSource: TypeAlias = Union[str, "os.PathLike[str]", bytes, bytearray, memoryview, IO[bytes]]
"""A file to upload: a path, the file's bytes, or a binary file object that can seek."""

_CHUNK_BYTES = 1024 * 1024
_CONTENT_TYPES = {
    "aac": "audio/aac",
    "aif": "audio/aiff",
    "aiff": "audio/aiff",
    "flac": "audio/flac",
    "m4a": "audio/mp4",
    "mp3": "audio/mpeg",
    "ogg": "audio/ogg",
    "wav": "audio/wav",
    "avif": "image/avif",
    "bmp": "image/bmp",
    "gif": "image/gif",
    "jpeg": "image/jpeg",
    "jpg": "image/jpeg",
    "png": "image/png",
    "tif": "image/tiff",
    "tiff": "image/tiff",
    "webp": "image/webp",
    "mp4": "video/mp4",
    "mov": "video/quicktime",
    "webm": "video/webm",
    "mkv": "video/x-matroska",
    "avi": "video/x-msvideo",
}


class ReadyUpload(Upload):
    """An upload whose Library asset is ready to use as a run input."""

    status: Literal["ready"]  # pyright: ignore[reportIncompatibleVariableOverride]
    asset_id: str = Field(alias="assetId")  # pyright: ignore[reportIncompatibleVariableOverride]


class _File:
    """A file to upload, which can be read again for each attempt to send it."""

    def __init__(self, file: UploadSource) -> None:
        self._data: bytes | None = None
        self._path: str | None = None
        self._stream: IO[bytes] | None = None
        self._start = 0
        self.name: str | None = None
        if isinstance(file, (bytes, bytearray, memoryview)):
            self._data = bytes(file)
            self.size = len(self._data)
        elif isinstance(file, (str, os.PathLike)):
            self._path = os.fspath(file)
            self.size = os.stat(self._path).st_size
            self.name = os.path.basename(self._path)
        else:
            if not file.seekable():
                raise ValueError("Pass a file object that can seek, or the file's bytes.")
            self._stream = file
            self._start = file.tell()
            self.size = file.seek(0, os.SEEK_END) - self._start
            file.seek(self._start)
            name = getattr(file, "name", None)
            self.name = os.path.basename(name) if isinstance(name, str) else None

    def content(self) -> bytes | Iterator[bytes]:
        return self._data if self._data is not None else self._chunks()

    def async_content(self) -> bytes | AsyncIterator[bytes]:
        return self._data if self._data is not None else self._async_chunks()

    def sha256(self) -> str:
        digest = hashlib.sha256()
        content = self.content()
        for chunk in [content] if isinstance(content, bytes) else content:
            digest.update(chunk)
        return digest.hexdigest()

    def _chunks(self) -> Iterator[bytes]:
        if self._stream is not None:
            self._stream.seek(self._start)
            while chunk := self._stream.read(_CHUNK_BYTES):
                yield chunk
        elif self._path is not None:
            with open(self._path, "rb") as stream:
                while chunk := stream.read(_CHUNK_BYTES):
                    yield chunk

    async def _async_chunks(self) -> AsyncIterator[bytes]:
        if self._stream is not None:
            stream = anyio.wrap_file(self._stream)
            await stream.seek(self._start)
            while chunk := await stream.read(_CHUNK_BYTES):
                yield chunk
        elif self._path is not None:
            async with await anyio.open_file(self._path, "rb") as stream:
                while chunk := await stream.read(_CHUNK_BYTES):
                    yield chunk


def _create_body(
    file: _File,
    filename: str | None,
    content_type: str | None,
    sha256: str,
    project_id: str | None,
    folder_id: str | None,
) -> dict[str, object]:
    name = filename or file.name
    if not name:
        raise ValueError("Pass filename to upload a file that has no name.")
    content_type = content_type or _CONTENT_TYPES.get(os.path.splitext(name)[1][1:].lower())
    if not content_type:
        raise ValueError(f"Pass content_type: {name} has no type ZeroGen recognizes.")
    body: dict[str, object] = {
        "filename": name,
        "contentType": content_type,
        "sizeBytes": file.size,
        "sha256": sha256,
    }
    if project_id is not None:
        body["projectId"] = project_id
    if folder_id is not None:
        body["folderId"] = folder_id
    return body


def _ready(upload: Upload) -> ReadyUpload:
    if upload.status != "ready" or upload.asset_id is None:
        raise RuntimeError(f"Upload {upload.id} isn't ready.")
    return ReadyUpload.model_validate(upload.model_dump(by_alias=True))


def _target(upload: Upload, file: _File) -> tuple[str, str, dict[str, str]]:
    if upload.upload is None:
        raise RuntimeError(f"Upload {upload.id} has no target to send the file to.")
    headers = {**upload.upload.headers, "Content-Length": str(file.size)}
    return upload.upload.method, upload.upload.url, headers


def _path(id: str) -> str:
    return f"/uploads/{quote(id, safe='')}"


class Uploads:
    def __init__(self, client: ZeroGen) -> None:
        self._client = client

    def upload(
        self,
        file: UploadSource,
        /,
        *,
        filename: str | None = None,
        content_type: str | None = None,
        project_id: str | None = None,
        folder_id: str | None = None,
        sha256: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> ReadyUpload:
        """Uploads a file into the Library and returns it when it's ready to use as a run input,
        with its `asset_id`.

        Args:
            file: A path, the file's bytes, or a binary file object that can seek.
            filename: Defaults to the name of the path or file object.
            content_type: Defaults to the type the filename's extension implies.
            project_id: The project to upload into; the organization's default project when
                omitted.
            folder_id: A folder in that project to add the asset to.
            sha256: The file's SHA-256 digest in lowercase hex, computed when omitted. An
                identical file already in the project is reused instead of uploaded again.
        """
        source = _File(file)
        body = _create_body(
            source,
            filename,
            content_type,
            sha256 or source.sha256(),
            project_id,
            folder_id,
        )
        upload = self._client._request(
            Upload.model_validate, "POST", "/uploads", body=body, options=options
        )
        if upload.status != "ready":
            method, url, headers = _target(upload, source)
            self._client._storage(
                method,
                url,
                headers=headers,
                content=source.content,
                timeout=options.get("timeout"),
                max_retries=options.get("max_retries", self._client.max_retries),
            )
            upload = self.complete(upload.id, **options)
        return _ready(upload)

    def create(self, body: CreateUploadRequest, /, **options: Unpack[PostRequestOptions]) -> Upload:
        """Starts an upload. `PUT` the file's bytes to the returned target, then complete it."""
        return self._client._request(
            Upload.model_validate, "POST", "/uploads", body=body, options=options
        )

    def get(self, id: str, /, **options: Unpack[RequestOptions]) -> Upload:
        """Reads one of your uploads."""
        return self._client._request(Upload.model_validate, "GET", _path(id), options=options)

    def complete(self, id: str, /, **options: Unpack[PostRequestOptions]) -> Upload:
        """Checks the uploaded bytes and makes them a Library asset. Completing again returns the
        same asset."""
        return self._client._request(
            Upload.model_validate, "POST", f"{_path(id)}/complete", options=options
        )


class AsyncUploads:
    def __init__(self, client: AsyncZeroGen) -> None:
        self._client = client

    async def upload(
        self,
        file: UploadSource,
        /,
        *,
        filename: str | None = None,
        content_type: str | None = None,
        project_id: str | None = None,
        folder_id: str | None = None,
        sha256: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> ReadyUpload:
        """Uploads a file into the Library and returns it when it's ready to use as a run input,
        with its `asset_id`.

        Args:
            file: A path, the file's bytes, or a binary file object that can seek.
            filename: Defaults to the name of the path or file object.
            content_type: Defaults to the type the filename's extension implies.
            project_id: The project to upload into; the organization's default project when
                omitted.
            folder_id: A folder in that project to add the asset to.
            sha256: The file's SHA-256 digest in lowercase hex, computed in a worker thread when
                omitted. An identical file already in the project is reused instead of uploaded
                again.
        """
        source = _File(file)
        body = _create_body(
            source,
            filename,
            content_type,
            sha256 or await anyio.to_thread.run_sync(source.sha256),
            project_id,
            folder_id,
        )
        upload = await self._client._request(
            Upload.model_validate, "POST", "/uploads", body=body, options=options
        )
        if upload.status != "ready":
            method, url, headers = _target(upload, source)
            await self._client._storage(
                method,
                url,
                headers=headers,
                content=source.async_content,
                timeout=options.get("timeout"),
                max_retries=options.get("max_retries", self._client.max_retries),
            )
            upload = await self.complete(upload.id, **options)
        return _ready(upload)

    async def create(
        self, body: CreateUploadRequest, /, **options: Unpack[PostRequestOptions]
    ) -> Upload:
        """Starts an upload. `PUT` the file's bytes to the returned target, then complete it."""
        return await self._client._request(
            Upload.model_validate, "POST", "/uploads", body=body, options=options
        )

    async def get(self, id: str, /, **options: Unpack[RequestOptions]) -> Upload:
        """Reads one of your uploads."""
        return await self._client._request(Upload.model_validate, "GET", _path(id), options=options)

    async def complete(self, id: str, /, **options: Unpack[PostRequestOptions]) -> Upload:
        """Checks the uploaded bytes and makes them a Library asset. Completing again returns the
        same asset."""
        return await self._client._request(
            Upload.model_validate, "POST", f"{_path(id)}/complete", options=options
        )
