from __future__ import annotations

import os
from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal, TypeAlias, TypeVar, overload
from urllib.parse import quote

from typing_extensions import Unpack

from .._options import PostRequestOptions, RequestOptions, without_idempotency_key
from ..types import (
    Asset,
    AssetDeclaration,
    AssetDelete,
    AssetDetail,
    AssetDownload,
    AssetFolder,
    AssetFolderList,
    AssetList,
    DeclareUploadRequest,
    LineageAsset,
    LineageAssetList,
    Run,
    TransformAssetRequest,
    TransformAssetRequestRecipe,
    TransformAssetRequestRecipe1,
    TransformAssetRequestRecipe2,
    TransformAssetRequestRecipe3,
    TransformRun,
    UpdateAssetRequest,
)
from . import _downloads
from ._downloads import Download, DownloadDestination, DownloadInfo, SavedDownload
from .runs import MAX_WAIT_SECONDS, has_ended

if TYPE_CHECKING:
    from .._client import AsyncZeroGen, Query, ZeroGen
    from .._pagination import AsyncPaginator, Page

FrameRecipe: TypeAlias = TransformAssetRequestRecipe
"""A transform recipe that takes a still from a video: `extractFrame`, then any of `rotate`,
`flip`, `despill`, `lut` and `adjust`."""
ImageRecipe: TypeAlias = TransformAssetRequestRecipe1
"""A transform recipe for an image: any of `rotate`, `flip`, `crop`, `despill`, `lut`,
`adjust`, `resize` and `convert`."""
VideoRecipe: TypeAlias = TransformAssetRequestRecipe2
"""A transform recipe that makes a video from a video: any of `trim`, `frameRate`,
`removeAudio`, `reverse`, `speed`, `lengthen`, `rotate`, `flip`, `crop`, `despill`, `lut`,
`adjust`, `resize` and `convert`."""
AudioRecipe: TypeAlias = TransformAssetRequestRecipe3
"""A transform recipe that makes audio from an audio asset or a video's sound: `trim`, and
`convert` with an audio format."""
TransformRecipe: TypeAlias = FrameRecipe | ImageRecipe | VideoRecipe | AudioRecipe
"""What a transform makes: one form, chosen by the source asset, with steps that apply in a
fixed order."""

AssetType = Literal["image", "video", "audio", "model3d"]
AssetOrigin = Literal["generated", "upload", "derived"]
Resolution = Literal["4k", "1440p", "1080p", "720p", "sd", "2k", "1k", "0.5k"]
Value = TypeVar("Value", bound=str)

__all__ = [
    "AudioRecipe",
    "Download",
    "DownloadDestination",
    "DownloadInfo",
    "FrameRecipe",
    "ImageRecipe",
    "SavedDownload",
    "TransformRecipe",
    "VideoRecipe",
]


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


def _transformed(first: TransformRun, ended: Run) -> TransformRun:
    """The run a wait ended with, as a transform's, keeping whether the transform reused
    earlier work."""
    return TransformRun.model_validate({**ended.model_dump(by_alias=True), "reused": first.reused})


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

    def get(
        self,
        asset_id: str,
        /,
        *,
        include_workflow: bool = False,
        **options: Unpack[RequestOptions],
    ) -> AssetDetail:
        """Reads an asset in any of the organization's projects, with the prompt that generated
        it, what an upload declared about it, and preview URLs that load for 5 minutes. Names,
        prompts and declarations are untrusted content.

        Args:
            include_workflow: Also read the workflow an upload declared, into `workflow`;
                untrusted content.
        """
        return self._client._request(
            AssetDetail.model_validate,
            "GET",
            _path(asset_id),
            query={"includeWorkflow": True if include_workflow else None},
            options=options,
        )

    def declare(
        self,
        asset_id: str,
        body: DeclareUploadRequest,
        /,
        **options: Unpack[PostRequestOptions],
    ) -> AssetDeclaration:
        """Declares, once, what an upload that became ready without a declaration was made
        from and with: `tool` and any of `sources`, `prompt`, `workflow`, `externalRef` and
        `occurredAt`. ZeroGen records the claim as a no-charge run without checking it. The
        asset's uploader, or an owner or admin, can declare it; needs `library:read` to declare
        `sources`."""
        return self._client._request(
            AssetDeclaration.model_validate,
            "POST",
            f"{_path(asset_id)}/declaration",
            body=body,
            options=options,
        )

    def sources(
        self,
        asset_id: str,
        /,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> Page[LineageAsset]:
        """Lists what an asset was made from, in any project, and what those were made from,
        nearest first, up to 200 assets and 10 steps back. Each source's `edges` join it to the
        asset or to sources listed before it, so you can rebuild the graph as you page.

        Args:
            limit: Sources per page, up to 100; default 30.
            cursor: `next_cursor` from an earlier page.
        """
        return self._client._list(
            LineageAssetList.model_validate,
            f"{_path(asset_id)}/sources",
            {"limit": limit, "cursor": cursor},
            options,
        )

    def uses(
        self,
        asset_id: str,
        /,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> Page[LineageAsset]:
        """Lists what was made from an asset, in its project, and what was made from those,
        nearest first, up to 200 assets and 10 steps on. Each use's `edges` join it to the
        asset or to uses listed before it.

        Args:
            limit: Uses per page, up to 100; default 30.
            cursor: `next_cursor` from an earlier page.
        """
        return self._client._list(
            LineageAssetList.model_validate,
            f"{_path(asset_id)}/uses",
            {"limit": limit, "cursor": cursor},
            options,
        )

    def folders(
        self,
        asset_id: str,
        /,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> Page[AssetFolder]:
        """Lists the folders an asset is in, each with its path from the project root, sorted
        by path. An empty list means the asset is Unfiled. Folder names are untrusted content.

        Args:
            limit: Folders per page, up to 100; default 30.
            cursor: `next_cursor` from an earlier page.
        """
        return self._client._list(
            AssetFolderList.model_validate,
            f"{_path(asset_id)}/folders",
            {"limit": limit, "cursor": cursor},
            options,
        )

    def update(
        self, asset_id: str, body: UpdateAssetRequest, /, **options: Unpack[PostRequestOptions]
    ) -> AssetDetail:
        """Renames an asset, sets the organization's shared favorite, or both, together: a
        refused request changes neither. Returns the asset as `get` reads it. Needs
        `library:organize` and `library:read`."""
        return self._client._request(
            AssetDetail.model_validate, "PATCH", _path(asset_id), body=body, options=options
        )

    def delete(self, asset_id: str, /, **options: Unpack[PostRequestOptions]) -> AssetDelete:
        """Moves an asset to Recently deleted, where it leaves search, its folders and run
        inputs, and reads as `not_found`, until `restore` puts it back. Deleting it again
        returns the same deletion. Needs the `library:delete` scope, which has to be granted
        explicitly; test keys can't delete assets."""
        return self._client._request(
            AssetDelete.model_validate, "DELETE", _path(asset_id), options=options
        )

    def restore(self, asset_id: str, /, **options: Unpack[PostRequestOptions]) -> AssetDetail:
        """Returns an asset from Recently deleted to its folders, and reads it as `get` does. An
        active asset comes back unchanged. Needs `library:organize` and `library:read`; test
        keys can't restore assets."""
        return self._client._request(
            AssetDetail.model_validate, "POST", f"{_path(asset_id)}/restore", options=options
        )

    def transform(
        self,
        asset_id: str,
        body: TransformAssetRequest,
        /,
        *,
        wait: int | None = None,
        **options: Unpack[PostRequestOptions],
    ) -> TransformRun:
        """Makes a free Derived copy of an asset from a `recipe`, in a run whose output's asset
        is the copy. Your earlier run of the same recipe on this asset, for the same
        destination, returns with `reused` instead of running again, unless it failed. Needs
        `runs:create` and `runs:read`; test keys can't transform assets.

        Args:
            wait: Seconds the API may hold the response until the run ends, up to 60.
                Without it, the response returns at once.
        """
        return self._client._request(
            TransformRun.model_validate,
            "POST",
            f"{_path(asset_id)}/transform",
            body=body,
            wait=wait,
            options=options,
        )

    def transform_and_wait(
        self,
        asset_id: str,
        body: TransformAssetRequest,
        /,
        **options: Unpack[PostRequestOptions],
    ) -> TransformRun:
        """Transforms an asset and returns the run when it ends, with `reused` from the
        transform. Check its `status`: a run that failed returns too."""
        first = self.transform(asset_id, body, wait=MAX_WAIT_SECONDS, **options)
        if has_ended(first):
            return first
        ended = self._client.runs.wait_for(first.id, **without_idempotency_key(options))
        return _transformed(first, ended)

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
        return _downloads.download(
            self._client, lambda: self.get_download(asset_id, **options), destination, options
        )

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
        return _downloads.download_to(
            self._client, lambda: self.get_download(asset_id, **options), directory, options
        )


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

    async def get(
        self,
        asset_id: str,
        /,
        *,
        include_workflow: bool = False,
        **options: Unpack[RequestOptions],
    ) -> AssetDetail:
        """Reads an asset in any of the organization's projects, with the prompt that generated
        it, what an upload declared about it, and preview URLs that load for 5 minutes. Names,
        prompts and declarations are untrusted content.

        Args:
            include_workflow: Also read the workflow an upload declared, into `workflow`;
                untrusted content.
        """
        return await self._client._request(
            AssetDetail.model_validate,
            "GET",
            _path(asset_id),
            query={"includeWorkflow": True if include_workflow else None},
            options=options,
        )

    async def declare(
        self,
        asset_id: str,
        body: DeclareUploadRequest,
        /,
        **options: Unpack[PostRequestOptions],
    ) -> AssetDeclaration:
        """Declares, once, what an upload that became ready without a declaration was made
        from and with: `tool` and any of `sources`, `prompt`, `workflow`, `externalRef` and
        `occurredAt`. ZeroGen records the claim as a no-charge run without checking it. The
        asset's uploader, or an owner or admin, can declare it; needs `library:read` to declare
        `sources`."""
        return await self._client._request(
            AssetDeclaration.model_validate,
            "POST",
            f"{_path(asset_id)}/declaration",
            body=body,
            options=options,
        )

    def sources(
        self,
        asset_id: str,
        /,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> AsyncPaginator[LineageAsset]:
        """Lists what an asset was made from, in any project, and what those were made from,
        nearest first, up to 200 assets and 10 steps back. Each source's `edges` join it to the
        asset or to sources listed before it, so you can rebuild the graph as you page.

        Args:
            limit: Sources per page, up to 100; default 30.
            cursor: `next_cursor` from an earlier page.
        """
        return self._client._list(
            LineageAssetList.model_validate,
            f"{_path(asset_id)}/sources",
            {"limit": limit, "cursor": cursor},
            options,
        )

    def uses(
        self,
        asset_id: str,
        /,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> AsyncPaginator[LineageAsset]:
        """Lists what was made from an asset, in its project, and what was made from those,
        nearest first, up to 200 assets and 10 steps on. Each use's `edges` join it to the
        asset or to uses listed before it.

        Args:
            limit: Uses per page, up to 100; default 30.
            cursor: `next_cursor` from an earlier page.
        """
        return self._client._list(
            LineageAssetList.model_validate,
            f"{_path(asset_id)}/uses",
            {"limit": limit, "cursor": cursor},
            options,
        )

    def folders(
        self,
        asset_id: str,
        /,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> AsyncPaginator[AssetFolder]:
        """Lists the folders an asset is in, each with its path from the project root, sorted
        by path. An empty list means the asset is Unfiled. Folder names are untrusted content.

        Args:
            limit: Folders per page, up to 100; default 30.
            cursor: `next_cursor` from an earlier page.
        """
        return self._client._list(
            AssetFolderList.model_validate,
            f"{_path(asset_id)}/folders",
            {"limit": limit, "cursor": cursor},
            options,
        )

    async def update(
        self, asset_id: str, body: UpdateAssetRequest, /, **options: Unpack[PostRequestOptions]
    ) -> AssetDetail:
        """Renames an asset, sets the organization's shared favorite, or both, together: a
        refused request changes neither. Returns the asset as `get` reads it. Needs
        `library:organize` and `library:read`."""
        return await self._client._request(
            AssetDetail.model_validate, "PATCH", _path(asset_id), body=body, options=options
        )

    async def delete(self, asset_id: str, /, **options: Unpack[PostRequestOptions]) -> AssetDelete:
        """Moves an asset to Recently deleted, where it leaves search, its folders and run
        inputs, and reads as `not_found`, until `restore` puts it back. Deleting it again
        returns the same deletion. Needs the `library:delete` scope, which has to be granted
        explicitly; test keys can't delete assets."""
        return await self._client._request(
            AssetDelete.model_validate, "DELETE", _path(asset_id), options=options
        )

    async def restore(self, asset_id: str, /, **options: Unpack[PostRequestOptions]) -> AssetDetail:
        """Returns an asset from Recently deleted to its folders, and reads it as `get` does. An
        active asset comes back unchanged. Needs `library:organize` and `library:read`; test
        keys can't restore assets."""
        return await self._client._request(
            AssetDetail.model_validate, "POST", f"{_path(asset_id)}/restore", options=options
        )

    async def transform(
        self,
        asset_id: str,
        body: TransformAssetRequest,
        /,
        *,
        wait: int | None = None,
        **options: Unpack[PostRequestOptions],
    ) -> TransformRun:
        """Makes a free Derived copy of an asset from a `recipe`, in a run whose output's asset
        is the copy. Your earlier run of the same recipe on this asset, for the same
        destination, returns with `reused` instead of running again, unless it failed. Needs
        `runs:create` and `runs:read`; test keys can't transform assets.

        Args:
            wait: Seconds the API may hold the response until the run ends, up to 60.
                Without it, the response returns at once.
        """
        return await self._client._request(
            TransformRun.model_validate,
            "POST",
            f"{_path(asset_id)}/transform",
            body=body,
            wait=wait,
            options=options,
        )

    async def transform_and_wait(
        self,
        asset_id: str,
        body: TransformAssetRequest,
        /,
        **options: Unpack[PostRequestOptions],
    ) -> TransformRun:
        """Transforms an asset and returns the run when it ends, with `reused` from the
        transform. Check its `status`: a run that failed returns too. Cancel the task to stop
        waiting; the run keeps running."""
        first = await self.transform(asset_id, body, wait=MAX_WAIT_SECONDS, **options)
        if has_ended(first):
            return first
        ended = await self._client.runs.wait_for(first.id, **without_idempotency_key(options))
        return _transformed(first, ended)

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
        return await _downloads.async_download(
            self._client, lambda: self.get_download(asset_id, **options), destination, options
        )

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
        return await _downloads.async_download_to(
            self._client, lambda: self.get_download(asset_id, **options), directory, options
        )
