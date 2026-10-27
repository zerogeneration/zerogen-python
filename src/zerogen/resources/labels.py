from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

from typing_extensions import Unpack

from .._options import PostRequestOptions, RequestOptions
from ..types import (
    CreateLabelRequest,
    Label,
    LabelAssetsChange,
    LabelAssetsRequest,
    LabelList,
    UpdateLabelRequest,
)

if TYPE_CHECKING:
    from .._client import AsyncZeroGen, ZeroGen
    from .._pagination import AsyncPaginator, Page


def _path(label_id: str) -> str:
    return f"/labels/{quote(label_id, safe='')}"


def _assets_path(project_id: str, label_id: str) -> str:
    return f"/projects/{quote(project_id, safe='')}/labels/{quote(label_id, safe='')}/assets"


class Labels:
    def __init__(self, client: ZeroGen) -> None:
        self._client = client

    def list(
        self,
        *,
        include_archived: bool | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> Page[Label]:
        """Lists the organization's active labels.

        Args:
            include_archived: Also list archived labels, for owners and admins.
            limit: Labels per page, up to 100; default 20.
            cursor: `next_cursor` from an earlier page, with the same filters.
        """
        return self._client._list(
            LabelList.model_validate,
            "/labels",
            {"includeArchived": include_archived, "limit": limit, "cursor": cursor},
            options,
        )

    def create(self, body: CreateLabelRequest, /, **options: Unpack[PostRequestOptions]) -> Label:
        """Creates an organization label; owners and admins only. A test key can't create
        labels."""
        return self._client._request(
            Label.model_validate, "POST", "/labels", body=body, options=options
        )

    def update(
        self, label_id: str, body: UpdateLabelRequest, /, **options: Unpack[RequestOptions]
    ) -> Label:
        """Replaces a label's name, description and color, so send all three; owners and admins
        only."""
        return self._client._request(
            Label.model_validate, "PUT", _path(label_id), body=body, options=options
        )

    def archive(self, label_id: str, /, **options: Unpack[PostRequestOptions]) -> Label:
        """Archives a label; owners and admins only. Its assets keep it, and `restore` undoes
        this."""
        return self._client._request(
            Label.model_validate, "POST", f"{_path(label_id)}/archive", options=options
        )

    def restore(self, label_id: str, /, **options: Unpack[PostRequestOptions]) -> Label:
        """Restores an archived label, with its assets; owners and admins only."""
        return self._client._request(
            Label.model_validate, "POST", f"{_path(label_id)}/restore", options=options
        )

    def add_assets(
        self,
        project_id: str,
        label_id: str,
        body: LabelAssetsRequest,
        /,
        **options: Unpack[PostRequestOptions],
    ) -> LabelAssetsChange:
        """Adds a label to up to 50 assets in a project, all or none."""
        return self._client._request(
            LabelAssetsChange.model_validate,
            "POST",
            _assets_path(project_id, label_id),
            body=body,
            options=options,
        )

    def remove_assets(
        self,
        project_id: str,
        label_id: str,
        body: LabelAssetsRequest,
        /,
        **options: Unpack[PostRequestOptions],
    ) -> LabelAssetsChange:
        """Removes a label from up to 50 assets in a project, all or none. The label itself
        stays."""
        return self._client._request(
            LabelAssetsChange.model_validate,
            "POST",
            f"{_assets_path(project_id, label_id)}/remove",
            body=body,
            options=options,
        )


class AsyncLabels:
    def __init__(self, client: AsyncZeroGen) -> None:
        self._client = client

    def list(
        self,
        *,
        include_archived: bool | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> AsyncPaginator[Label]:
        """Lists the organization's active labels.

        Args:
            include_archived: Also list archived labels, for owners and admins.
            limit: Labels per page, up to 100; default 20.
            cursor: `next_cursor` from an earlier page, with the same filters.
        """
        return self._client._list(
            LabelList.model_validate,
            "/labels",
            {"includeArchived": include_archived, "limit": limit, "cursor": cursor},
            options,
        )

    async def create(
        self, body: CreateLabelRequest, /, **options: Unpack[PostRequestOptions]
    ) -> Label:
        """Creates an organization label; owners and admins only. A test key can't create
        labels."""
        return await self._client._request(
            Label.model_validate, "POST", "/labels", body=body, options=options
        )

    async def update(
        self, label_id: str, body: UpdateLabelRequest, /, **options: Unpack[RequestOptions]
    ) -> Label:
        """Replaces a label's name, description and color, so send all three; owners and admins
        only."""
        return await self._client._request(
            Label.model_validate, "PUT", _path(label_id), body=body, options=options
        )

    async def archive(self, label_id: str, /, **options: Unpack[PostRequestOptions]) -> Label:
        """Archives a label; owners and admins only. Its assets keep it, and `restore` undoes
        this."""
        return await self._client._request(
            Label.model_validate, "POST", f"{_path(label_id)}/archive", options=options
        )

    async def restore(self, label_id: str, /, **options: Unpack[PostRequestOptions]) -> Label:
        """Restores an archived label, with its assets; owners and admins only."""
        return await self._client._request(
            Label.model_validate, "POST", f"{_path(label_id)}/restore", options=options
        )

    async def add_assets(
        self,
        project_id: str,
        label_id: str,
        body: LabelAssetsRequest,
        /,
        **options: Unpack[PostRequestOptions],
    ) -> LabelAssetsChange:
        """Adds a label to up to 50 assets in a project, all or none."""
        return await self._client._request(
            LabelAssetsChange.model_validate,
            "POST",
            _assets_path(project_id, label_id),
            body=body,
            options=options,
        )

    async def remove_assets(
        self,
        project_id: str,
        label_id: str,
        body: LabelAssetsRequest,
        /,
        **options: Unpack[PostRequestOptions],
    ) -> LabelAssetsChange:
        """Removes a label from up to 50 assets in a project, all or none. The label itself
        stays."""
        return await self._client._request(
            LabelAssetsChange.model_validate,
            "POST",
            f"{_assets_path(project_id, label_id)}/remove",
            body=body,
            options=options,
        )
