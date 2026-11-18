from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

from typing_extensions import Unpack

from .._options import PostRequestOptions, RequestOptions
from ..types import (
    AssetBatchChange,
    AssetBatchRequest,
    CreateLabelRequest,
    Label,
    LabelList,
    UpdateLabelRequest,
)

if TYPE_CHECKING:
    from .._client import AsyncZeroGen, ZeroGen
    from .._pagination import AsyncPaginator, Page


def _path(label_id: str) -> str:
    return f"/labels/{quote(label_id, safe='')}"


def _assets_path(label_id: str) -> str:
    return f"{_path(label_id)}/assets"


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

    def get(self, label_id: str, /, **options: Unpack[RequestOptions]) -> Label:
        """Reads an organization label. An archived label reads only for owners and
        admins."""
        return self._client._request(Label.model_validate, "GET", _path(label_id), options=options)

    def update(
        self, label_id: str, body: UpdateLabelRequest, /, **options: Unpack[PostRequestOptions]
    ) -> Label:
        """Changes a label's name, description or color, keeping the fields you leave out;
        owners and admins only."""
        return self._client._request(
            Label.model_validate, "PATCH", _path(label_id), body=body, options=options
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
        label_id: str,
        body: AssetBatchRequest,
        /,
        **options: Unpack[PostRequestOptions],
    ) -> AssetBatchChange:
        """Adds a label to up to 100 assets, in any of the organization's projects, all or
        none. Returns the assets it changed and those that already had it."""
        return self._client._request(
            AssetBatchChange.model_validate,
            "POST",
            _assets_path(label_id),
            body=body,
            options=options,
        )

    def remove_assets(
        self,
        label_id: str,
        body: AssetBatchRequest,
        /,
        **options: Unpack[PostRequestOptions],
    ) -> AssetBatchChange:
        """Removes a label from up to 100 assets, in any of the organization's projects, all
        or none. The label itself stays. Returns the assets it changed and those that didn't
        have it."""
        return self._client._request(
            AssetBatchChange.model_validate,
            "POST",
            f"{_assets_path(label_id)}/remove",
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

    async def get(self, label_id: str, /, **options: Unpack[RequestOptions]) -> Label:
        """Reads an organization label. An archived label reads only for owners and
        admins."""
        return await self._client._request(
            Label.model_validate, "GET", _path(label_id), options=options
        )

    async def update(
        self, label_id: str, body: UpdateLabelRequest, /, **options: Unpack[PostRequestOptions]
    ) -> Label:
        """Changes a label's name, description or color, keeping the fields you leave out;
        owners and admins only."""
        return await self._client._request(
            Label.model_validate, "PATCH", _path(label_id), body=body, options=options
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
        label_id: str,
        body: AssetBatchRequest,
        /,
        **options: Unpack[PostRequestOptions],
    ) -> AssetBatchChange:
        """Adds a label to up to 100 assets, in any of the organization's projects, all or
        none. Returns the assets it changed and those that already had it."""
        return await self._client._request(
            AssetBatchChange.model_validate,
            "POST",
            _assets_path(label_id),
            body=body,
            options=options,
        )

    async def remove_assets(
        self,
        label_id: str,
        body: AssetBatchRequest,
        /,
        **options: Unpack[PostRequestOptions],
    ) -> AssetBatchChange:
        """Removes a label from up to 100 assets, in any of the organization's projects, all
        or none. The label itself stays. Returns the assets it changed and those that didn't
        have it."""
        return await self._client._request(
            AssetBatchChange.model_validate,
            "POST",
            f"{_assets_path(label_id)}/remove",
            body=body,
            options=options,
        )
