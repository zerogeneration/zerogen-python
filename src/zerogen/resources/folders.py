from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal
from urllib.parse import quote

from typing_extensions import Unpack

from .._options import PostRequestOptions, RequestOptions
from ..types import (
    CreateFolderRequest,
    Folder,
    FolderAssetsChange,
    FolderAssetsRequest,
    FolderDelete,
    FolderList,
    FolderRestore,
    MoveAssetsRequest,
    RestoreFolderRequest,
    UpdateFolderRequest,
)

if TYPE_CHECKING:
    from .._client import AsyncZeroGen, ZeroGen
    from .._pagination import AsyncPaginator, Page


def _path(project_id: str, folder_id: str | None = None) -> str:
    path = f"/projects/{quote(project_id, safe='')}/folders"
    return path if folder_id is None else f"{path}/{quote(folder_id, safe='')}"


def _names(path: str | Sequence[str]) -> list[str]:
    """A path's folder names: a string splits on `/` and skips empty parts, and a list is taken
    as it is, so a name can contain `/`."""
    names = [name for name in path.split("/") if name.strip()] if isinstance(path, str) else [*path]
    if not names:
        raise ValueError("A folder path needs at least one folder name.")
    return names


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
        """Creates a folder at the project root or under `parentId`. With `reuseExisting`, a
        folder of that name already under the parent is returned instead. A test key can't
        create folders."""
        return self._client._request(
            Folder.model_validate, "POST", _path(project_id), body=body, options=options
        )

    def ensure_path(
        self,
        project_id: str,
        path: str | Sequence[str],
        /,
        *,
        parent_id: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> Folder:
        """Returns the folder at `path`, such as `"SH010/anim"`, creating each folder on the
        way that isn't there yet. Each level is a create with `reuseExisting`, which returns the
        folder of that name already under its parent, so clients filing into the same path at
        once share its folders. A test key can't create folders.

        Args:
            path: Folder names from `parent_id`, or from the project root. A string splits on
                `/`; pass a list when a name contains `/`.
            parent_id: The folder the path starts under; default the project root.
        """
        folder: Folder | None = None
        for name in _names(path):
            body: CreateFolderRequest = {"name": name, "parentId": parent_id, "reuseExisting": True}
            folder = self.create(project_id, body, **options)
            parent_id = folder.id
        assert folder is not None
        return folder

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

    def delete(
        self,
        project_id: str,
        folder_id: str,
        /,
        *,
        assets: Literal["keep", "trash"],
        **options: Unpack[PostRequestOptions],
    ) -> FolderDelete:
        """Deletes a folder and its subfolders. The response's `event_id` undoes your deletion
        within one hour, through `restore`. Only admins can delete LucidLink-linked folders.
        Needs the `library:delete` scope, which has to be granted explicitly; test keys can't
        delete folders.

        Args:
            assets: `"keep"` preserves the assets; `"trash"` sends them to Recently deleted,
                including assets in other folders. Use `"trash"` only when explicitly requested.
        """
        return self._client._request(
            FolderDelete.model_validate,
            "DELETE",
            _path(project_id, folder_id),
            query={"assets": assets},
            options=options,
        )

    def restore(
        self,
        project_id: str,
        body: RestoreFolderRequest,
        /,
        **options: Unpack[PostRequestOptions],
    ) -> FolderRestore:
        """Undoes your own folder deletion within one hour, with the `eventId` its response
        gave. Restores folders, placements and assets still trashed by that deletion. Needs the
        `library:organize` scope; test keys can't restore folders."""
        return self._client._request(
            FolderRestore.model_validate,
            "POST",
            f"{_path(project_id)}/restore",
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
        """Creates a folder at the project root or under `parentId`. With `reuseExisting`, a
        folder of that name already under the parent is returned instead. A test key can't
        create folders."""
        return await self._client._request(
            Folder.model_validate, "POST", _path(project_id), body=body, options=options
        )

    async def ensure_path(
        self,
        project_id: str,
        path: str | Sequence[str],
        /,
        *,
        parent_id: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> Folder:
        """Returns the folder at `path`, such as `"SH010/anim"`, creating each folder on the
        way that isn't there yet. Each level is a create with `reuseExisting`, which returns the
        folder of that name already under its parent, so clients filing into the same path at
        once share its folders. A test key can't create folders.

        Args:
            path: Folder names from `parent_id`, or from the project root. A string splits on
                `/`; pass a list when a name contains `/`.
            parent_id: The folder the path starts under; default the project root.
        """
        folder: Folder | None = None
        for name in _names(path):
            body: CreateFolderRequest = {"name": name, "parentId": parent_id, "reuseExisting": True}
            folder = await self.create(project_id, body, **options)
            parent_id = folder.id
        assert folder is not None
        return folder

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

    async def delete(
        self,
        project_id: str,
        folder_id: str,
        /,
        *,
        assets: Literal["keep", "trash"],
        **options: Unpack[PostRequestOptions],
    ) -> FolderDelete:
        """Deletes a folder and its subfolders. The response's `event_id` undoes your deletion
        within one hour, through `restore`. Only admins can delete LucidLink-linked folders.
        Needs the `library:delete` scope, which has to be granted explicitly; test keys can't
        delete folders.

        Args:
            assets: `"keep"` preserves the assets; `"trash"` sends them to Recently deleted,
                including assets in other folders. Use `"trash"` only when explicitly requested.
        """
        return await self._client._request(
            FolderDelete.model_validate,
            "DELETE",
            _path(project_id, folder_id),
            query={"assets": assets},
            options=options,
        )

    async def restore(
        self,
        project_id: str,
        body: RestoreFolderRequest,
        /,
        **options: Unpack[PostRequestOptions],
    ) -> FolderRestore:
        """Undoes your own folder deletion within one hour, with the `eventId` its response
        gave. Restores folders, placements and assets still trashed by that deletion. Needs the
        `library:organize` scope; test keys can't restore folders."""
        return await self._client._request(
            FolderRestore.model_validate,
            "POST",
            f"{_path(project_id)}/restore",
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
