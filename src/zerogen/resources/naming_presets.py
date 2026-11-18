from __future__ import annotations

from typing import TYPE_CHECKING

from typing_extensions import Unpack

from .._options import PostRequestOptions, RequestOptions
from ..types import CreateNamingPresetRequest, NamingPreset, NamingPresetList

if TYPE_CHECKING:
    from .._client import AsyncZeroGen, ZeroGen
    from .._pagination import AsyncPaginator, Page


class NamingPresets:
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
    ) -> Page[NamingPreset]:
        """Lists a project's shared naming presets. Pass one's `id` and field values as a run's
        `naming`.

        Args:
            limit: Presets per page, up to 100; default 20.
            cursor: `next_cursor` from an earlier page.
        """
        return self._client._list(
            NamingPresetList.model_validate,
            "/naming-presets",
            {"projectId": project_id, "limit": limit, "cursor": cursor},
            options,
        )

    def create(
        self, body: CreateNamingPresetRequest, /, **options: Unpack[PostRequestOptions]
    ) -> NamingPreset:
        """Saves a naming preset for everyone in `projectId`; owners and admins only. Fields
        run in order, joined by `delimiter`, and a `version` field belongs last. A test key
        can't create presets."""
        return self._client._request(
            NamingPreset.model_validate, "POST", "/naming-presets", body=body, options=options
        )


class AsyncNamingPresets:
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
    ) -> AsyncPaginator[NamingPreset]:
        """Lists a project's shared naming presets. Pass one's `id` and field values as a run's
        `naming`.

        Args:
            limit: Presets per page, up to 100; default 20.
            cursor: `next_cursor` from an earlier page.
        """
        return self._client._list(
            NamingPresetList.model_validate,
            "/naming-presets",
            {"projectId": project_id, "limit": limit, "cursor": cursor},
            options,
        )

    async def create(
        self, body: CreateNamingPresetRequest, /, **options: Unpack[PostRequestOptions]
    ) -> NamingPreset:
        """Saves a naming preset for everyone in `projectId`; owners and admins only. Fields
        run in order, joined by `delimiter`, and a `version` field belongs last. A test key
        can't create presets."""
        return await self._client._request(
            NamingPreset.model_validate, "POST", "/naming-presets", body=body, options=options
        )
