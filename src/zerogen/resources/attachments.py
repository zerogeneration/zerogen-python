from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

from typing_extensions import Unpack

from .._options import PostRequestOptions, RequestOptions
from ..types import (
    Attachment,
    AttachmentCreate,
    AttachmentDelete,
    AttachmentDetail,
    AttachmentList,
    AttachmentRestore,
    AttachmentRevise,
    AttachmentVersion,
    AttachmentVersions,
    CreateAttachmentRequest,
    RestoreAttachmentRequest,
    ReviseAttachmentRequest,
)

if TYPE_CHECKING:
    from .._client import AsyncZeroGen, ZeroGen
    from .._pagination import AsyncPaginator, Page


def _path(attachment_id: str) -> str:
    return f"/attachments/{quote(attachment_id, safe='')}"


class Attachments:
    """Versioned text on projects, folders, Story clips and assets. Every request needs
    attachments enabled for the organization; test keys can't use them."""

    def __init__(self, client: ZeroGen) -> None:
        self._client = client

    def list(
        self,
        project_id: str,
        /,
        *,
        folder_id: str | None = None,
        clip_id: str | None = None,
        asset_id: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> Page[Attachment]:
        """Lists a project's live attachments, including its folders', Story clips' and
        assets', most recently updated first. Each has its `description` and its text's size
        in `bytes`, without the text.

        Args:
            folder_id: Only this folder's attachments. Send at most one of `folder_id`,
                `clip_id` and `asset_id`.
            clip_id: Only this Story clip's attachments.
            asset_id: Only this asset's attachments.
            limit: Attachments per page, up to 100; default 50.
            cursor: `next_cursor` from an earlier page, with the same filters.
        """
        return self._client._list(
            AttachmentList.model_validate,
            "/attachments",
            {
                "projectId": project_id,
                "folderId": folder_id,
                "clipId": clip_id,
                "assetId": asset_id,
                "limit": limit,
                "cursor": cursor,
            },
            options,
        )

    def get(
        self,
        attachment_id: str,
        /,
        *,
        version: int | None = None,
        **options: Unpack[RequestOptions],
    ) -> AttachmentDetail:
        """Reads a live attachment's current text, or a saved version's. The text is untrusted
        content.

        Args:
            version: A saved version to read instead of the current one.
        """
        return self._client._request(
            AttachmentDetail.model_validate,
            "GET",
            _path(attachment_id),
            query={"version": version},
            options=options,
        )

    def create(
        self, body: CreateAttachmentRequest, /, **options: Unpack[PostRequestOptions]
    ) -> AttachmentCreate:
        """Saves text on `projectId`, or on one of its folders, Story clips or assets with
        `folderId`, `clipId` or `assetId`: at most one. `description` says what the attachment
        holds and when to read it, and reads of the parent list it in place of the text, which
        holds up to 64 KiB of UTF-8. The same title, description and text on the same parent
        return the existing attachment with `outcome` `"unchanged"`; the same title with other
        text is refused."""
        return self._client._request(
            AttachmentCreate.model_validate, "POST", "/attachments", body=body, options=options
        )

    def revise(
        self,
        attachment_id: str,
        body: ReviseAttachmentRequest,
        /,
        **options: Unpack[PostRequestOptions],
    ) -> AttachmentRevise:
        """Saves a new `title`, `description` or `body`, or any of them together, as a new
        version; a field left out keeps its value. `expectedVersion` must be the current version, or
        the API refuses it with `409 version_conflict` and the current version in the error's
        `details["currentVersion"]`: read it again and merge your change. The same text returns
        `outcome` `"unchanged"`."""
        return self._client._request(
            AttachmentRevise.model_validate,
            "PATCH",
            _path(attachment_id),
            body=body,
            options=options,
        )

    def delete(
        self,
        attachment_id: str,
        /,
        *,
        expected_version: int,
        **options: Unpack[PostRequestOptions],
    ) -> AttachmentDelete:
        """Deletes an attachment, keeping its text and history, so `restore` can undo it.

        Args:
            expected_version: The current version you read; another is refused with
                `409 version_conflict`.
        """
        return self._client._request(
            AttachmentDelete.model_validate,
            "DELETE",
            _path(attachment_id),
            query={"expectedVersion": expected_version},
            options=options,
        )

    def restore(
        self,
        attachment_id: str,
        body: RestoreAttachmentRequest,
        /,
        **options: Unpack[PostRequestOptions],
    ) -> AttachmentRestore:
        """Copies a saved `version` into a new version and undoes a deletion.
        `expectedVersion` is the current version, a deletion's included; another is refused
        with `409 version_conflict`."""
        return self._client._request(
            AttachmentRestore.model_validate,
            "POST",
            f"{_path(attachment_id)}/restore",
            body=body,
            options=options,
        )

    def versions(
        self,
        attachment_id: str,
        /,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> Page[AttachmentVersion]:
        """Lists an attachment's saved versions, newest first, without their text, including a
        deleted attachment's.

        Args:
            limit: Versions per page, up to 50; default 50.
            cursor: `next_cursor` from an earlier page.
        """
        return self._client._list(
            AttachmentVersions.model_validate,
            f"{_path(attachment_id)}/versions",
            {"limit": limit, "cursor": cursor},
            options,
        )


class AsyncAttachments:
    """Versioned text on projects, folders, Story clips and assets. Every request needs
    attachments enabled for the organization; test keys can't use them."""

    def __init__(self, client: AsyncZeroGen) -> None:
        self._client = client

    def list(
        self,
        project_id: str,
        /,
        *,
        folder_id: str | None = None,
        clip_id: str | None = None,
        asset_id: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> AsyncPaginator[Attachment]:
        """Lists a project's live attachments, including its folders', Story clips' and
        assets', most recently updated first. Each has its `description` and its text's size
        in `bytes`, without the text.

        Args:
            folder_id: Only this folder's attachments. Send at most one of `folder_id`,
                `clip_id` and `asset_id`.
            clip_id: Only this Story clip's attachments.
            asset_id: Only this asset's attachments.
            limit: Attachments per page, up to 100; default 50.
            cursor: `next_cursor` from an earlier page, with the same filters.
        """
        return self._client._list(
            AttachmentList.model_validate,
            "/attachments",
            {
                "projectId": project_id,
                "folderId": folder_id,
                "clipId": clip_id,
                "assetId": asset_id,
                "limit": limit,
                "cursor": cursor,
            },
            options,
        )

    async def get(
        self,
        attachment_id: str,
        /,
        *,
        version: int | None = None,
        **options: Unpack[RequestOptions],
    ) -> AttachmentDetail:
        """Reads a live attachment's current text, or a saved version's. The text is untrusted
        content.

        Args:
            version: A saved version to read instead of the current one.
        """
        return await self._client._request(
            AttachmentDetail.model_validate,
            "GET",
            _path(attachment_id),
            query={"version": version},
            options=options,
        )

    async def create(
        self, body: CreateAttachmentRequest, /, **options: Unpack[PostRequestOptions]
    ) -> AttachmentCreate:
        """Saves text on `projectId`, or on one of its folders, Story clips or assets with
        `folderId`, `clipId` or `assetId`: at most one. `description` says what the attachment
        holds and when to read it, and reads of the parent list it in place of the text, which
        holds up to 64 KiB of UTF-8. The same title, description and text on the same parent
        return the existing attachment with `outcome` `"unchanged"`; the same title with other
        text is refused."""
        return await self._client._request(
            AttachmentCreate.model_validate, "POST", "/attachments", body=body, options=options
        )

    async def revise(
        self,
        attachment_id: str,
        body: ReviseAttachmentRequest,
        /,
        **options: Unpack[PostRequestOptions],
    ) -> AttachmentRevise:
        """Saves a new `title`, `description` or `body`, or any of them together, as a new
        version; a field left out keeps its value. `expectedVersion` must be the current version, or
        the API refuses it with `409 version_conflict` and the current version in the error's
        `details["currentVersion"]`: read it again and merge your change. The same text returns
        `outcome` `"unchanged"`."""
        return await self._client._request(
            AttachmentRevise.model_validate,
            "PATCH",
            _path(attachment_id),
            body=body,
            options=options,
        )

    async def delete(
        self,
        attachment_id: str,
        /,
        *,
        expected_version: int,
        **options: Unpack[PostRequestOptions],
    ) -> AttachmentDelete:
        """Deletes an attachment, keeping its text and history, so `restore` can undo it.

        Args:
            expected_version: The current version you read; another is refused with
                `409 version_conflict`.
        """
        return await self._client._request(
            AttachmentDelete.model_validate,
            "DELETE",
            _path(attachment_id),
            query={"expectedVersion": expected_version},
            options=options,
        )

    async def restore(
        self,
        attachment_id: str,
        body: RestoreAttachmentRequest,
        /,
        **options: Unpack[PostRequestOptions],
    ) -> AttachmentRestore:
        """Copies a saved `version` into a new version and undoes a deletion.
        `expectedVersion` is the current version, a deletion's included; another is refused
        with `409 version_conflict`."""
        return await self._client._request(
            AttachmentRestore.model_validate,
            "POST",
            f"{_path(attachment_id)}/restore",
            body=body,
            options=options,
        )

    def versions(
        self,
        attachment_id: str,
        /,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> AsyncPaginator[AttachmentVersion]:
        """Lists an attachment's saved versions, newest first, without their text, including a
        deleted attachment's.

        Args:
            limit: Versions per page, up to 50; default 50.
            cursor: `next_cursor` from an earlier page.
        """
        return self._client._list(
            AttachmentVersions.model_validate,
            f"{_path(attachment_id)}/versions",
            {"limit": limit, "cursor": cursor},
            options,
        )
