from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

from typing_extensions import Unpack

from .._options import RequestOptions
from ..types import NamingPreset, NamingPresetList

if TYPE_CHECKING:
    from .._client import AsyncZeroGen, ZeroGen
    from .._pagination import AsyncPaginator, Page


def _path(project_id: str) -> str:
    return f"/projects/{quote(project_id, safe='')}/naming-presets"


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
            _path(project_id),
            {"limit": limit, "cursor": cursor},
            options,
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
            _path(project_id),
            {"limit": limit, "cursor": cursor},
            options,
        )
