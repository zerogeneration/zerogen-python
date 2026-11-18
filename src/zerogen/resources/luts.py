from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias

from typing_extensions import Unpack

from .._options import RequestOptions
from ..types import LutList, LutListDatum

if TYPE_CHECKING:
    from .._client import AsyncZeroGen, ZeroGen
    from .._pagination import AsyncPaginator, Page

Lut: TypeAlias = LutListDatum
"""One of the organization's LUTs, to name as `lut.lutId` in a transform's recipe."""


class Luts:
    def __init__(self, client: ZeroGen) -> None:
        self._client = client

    def list(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> Page[Lut]:
        """Lists the organization's LUTs, newest first, to name as `lut.lutId` in a transform's
        recipe. Each one's `input_color` says what footage it was made for. People add and
        remove LUTs in ZeroGen. A test key lists none.

        Args:
            limit: LUTs per page, up to 100; default 50.
            cursor: `next_cursor` from an earlier page.
        """
        return self._client._list(
            LutList.model_validate, "/luts", {"limit": limit, "cursor": cursor}, options
        )


class AsyncLuts:
    def __init__(self, client: AsyncZeroGen) -> None:
        self._client = client

    def list(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> AsyncPaginator[Lut]:
        """Lists the organization's LUTs, newest first, to name as `lut.lutId` in a transform's
        recipe. Each one's `input_color` says what footage it was made for. People add and
        remove LUTs in ZeroGen. A test key lists none.

        Args:
            limit: LUTs per page, up to 100; default 50.
            cursor: `next_cursor` from an earlier page.
        """
        return self._client._list(
            LutList.model_validate, "/luts", {"limit": limit, "cursor": cursor}, options
        )
