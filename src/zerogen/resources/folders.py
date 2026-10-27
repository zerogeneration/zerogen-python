from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

from typing_extensions import Unpack

from .._options import PostRequestOptions, RequestOptions
from ..types import (
    CreateFolderRequest,
    Folder,
    FolderAssetsChange,
    FolderAssetsRequest,
    FolderList,
    MoveAssetsRequest,
    UpdateFolderRequest,
)

if TYPE_CHECKING:
    from .._client import AsyncZeroGen, ZeroGen
    from .._pagination import AsyncPaginator, Page


def _path(project_id: str, folder_id: str | None = None) -> str:
    path = f"/projects/{quote(project_id, safe='')}/folders"
    return path if folder_id is None else f"{path}/{quote(folder_id, safe='')}"


class Folders:
    def __init__(self, client: ZeroGen) -> None:
        self._client = client

    def list(
        self,
        project_id: str,
        /,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> Page[Folder]:
        """Lists a project's folders, each with its parent, to assemble the folder tree.

        Args:
            limit: Folders per page, up to 100; default 50.
            cursor: `next_cursor` from an earlier page.
        """
        return self._client._list(
            FolderList.model_validate,
            _path(project_id),
            {"limit": limit, "cursor": cursor},
            options,
        )

    def create(
        self,
        project_id: str,
        body: CreateFolderRequest,
        /,
        **options: Unpack[PostRequestOptions],
    ) -> Folder:
        """Creates a folder at the project root or under `parentId`. A test key can't create
        folders."""
        return self._client._request(
            Folder.model_validate, "POST", _path(project_id), body=body, options=options
        )

    def update(
        self,
        project_id: str,
        folder_id: str,
        body: UpdateFolderRequest,
        /,
        **options: Unpack[RequestOptions],
    ) -> Folder:
        """Renames a folder, moves it under another parent (or to the project root with
        `parentId` None), or both. Its assets and subfolders keep their IDs."""
        return self._client._request(
            Folder.model_validate,
            "PATCH",
            _path(project_id, folder_id),
            body=body,
            options=options,
        )

    def add_assets(
        self,
        project_id: str,
        folder_id: str,
        body: FolderAssetsRequest,
        /,
        **options: Unpack[PostRequestOptions],
    ) -> FolderAssetsChange:
        """Adds up to 100 assets to a folder, keeping their other folders."""
        return self._client._request(
            FolderAssetsChange.model_validate,
            "POST",
            f"{_path(project_id, folder_id)}/assets",
            body=body,
            options=options,
        )

    def move_assets(
        self,
        project_id: str,
        folder_id: str,
        body: MoveAssetsRequest,
        /,
        **options: Unpack[PostRequestOptions],
    ) -> FolderAssetsChange:
        """Moves up to 100 assets out of `fromFolderId` and into a folder; their other folders
        keep them."""
        return self._client._request(
            FolderAssetsChange.model_validate,
            "POST",
            f"{_path(project_id, folder_id)}/assets/move",
            body=body,
            options=options,
        )

    def remove_assets(
        self,
        project_id: str,
        folder_id: str,
        body: FolderAssetsRequest,
        /,
        **options: Unpack[PostRequestOptions],
    ) -> FolderAssetsChange:
        """Takes up to 100 assets out of a folder. They stay in the Library and in their other
        folders."""
        return self._client._request(
            FolderAssetsChange.model_validate,
            "POST",
            f"{_path(project_id, folder_id)}/assets/remove",
            body=body,
            options=options,
        )


class AsyncFolders:
    def __init__(self, client: AsyncZeroGen) -> None:
        self._client = client

    def list(
        self,
        project_id: str,
        /,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> AsyncPaginator[Folder]:
        """Lists a project's folders, each with its parent, to assemble the folder tree.

        Args:
            limit: Folders per page, up to 100; default 50.
            cursor: `next_cursor` from an earlier page.
        """
        return self._client._list(
            FolderList.model_validate,
            _path(project_id),
            {"limit": limit, "cursor": cursor},
            options,
        )

    async def create(
        self,
        project_id: str,
        body: CreateFolderRequest,
        /,
        **options: Unpack[PostRequestOptions],
    ) -> Folder:
        """Creates a folder at the project root or under `parentId`. A test key can't create
        folders."""
        return await self._client._request(
            Folder.model_validate, "POST", _path(project_id), body=body, options=options
        )

    async def update(
        self,
        project_id: str,
        folder_id: str,
        body: UpdateFolderRequest,
        /,
        **options: Unpack[RequestOptions],
    ) -> Folder:
        """Renames a folder, moves it under another parent (or to the project root with
        `parentId` None), or both. Its assets and subfolders keep their IDs."""
        return await self._client._request(
            Folder.model_validate,
            "PATCH",
            _path(project_id, folder_id),
            body=body,
            options=options,
        )

    async def add_assets(
        self,
        project_id: str,
        folder_id: str,
        body: FolderAssetsRequest,
        /,
        **options: Unpack[PostRequestOptions],
    ) -> FolderAssetsChange:
        """Adds up to 100 assets to a folder, keeping their other folders."""
        return await self._client._request(
            FolderAssetsChange.model_validate,
            "POST",
            f"{_path(project_id, folder_id)}/assets",
            body=body,
            options=options,
        )

    async def move_assets(
        self,
        project_id: str,
        folder_id: str,
        body: MoveAssetsRequest,
        /,
        **options: Unpack[PostRequestOptions],
    ) -> FolderAssetsChange:
        """Moves up to 100 assets out of `fromFolderId` and into a folder; their other folders
        keep them."""
        return await self._client._request(
            FolderAssetsChange.model_validate,
            "POST",
            f"{_path(project_id, folder_id)}/assets/move",
            body=body,
            options=options,
        )

    async def remove_assets(
        self,
        project_id: str,
        folder_id: str,
        body: FolderAssetsRequest,
        /,
        **options: Unpack[PostRequestOptions],
    ) -> FolderAssetsChange:
        """Takes up to 100 assets out of a folder. They stay in the Library and in their other
        folders."""
        return await self._client._request(
            FolderAssetsChange.model_validate,
            "POST",
            f"{_path(project_id, folder_id)}/assets/remove",
            body=body,
            options=options,
        )
