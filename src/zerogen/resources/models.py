from __future__ import annotations

from typing import TYPE_CHECKING, Literal
from urllib.parse import quote

from typing_extensions import Unpack

from .._options import RequestOptions
from ..types import Model, ModelDetail, ModelList

if TYPE_CHECKING:
    from .._client import AsyncZeroGen, Query, ZeroGen
    from .._pagination import AsyncPaginator, Page


def _path(id: str) -> str:
    return "/models/" + "/".join(quote(segment, safe="") for segment in id.split("/"))


def _query(
    capability: str | None,
    operation: str | None,
    q: str | None,
    frames: str | None,
    audio: bool | None,
    reference_kind: str | None,
    limit: int | None,
    cursor: str | None,
) -> Query:
    return {
        "capability": capability,
        "operation": operation,
        "q": q,
        "frames": frames,
        "audio": True if audio else None,
        "referenceKind": reference_kind,
        "limit": limit,
        "cursor": cursor,
    }


class Models:
    def __init__(self, client: ZeroGen) -> None:
        self._client = client

    def list(
        self,
        *,
        capability: Literal["image", "video"] | None = None,
        operation: str | None = None,
        q: str | None = None,
        frames: Literal["start", "start-end"] | None = None,
        audio: bool | None = None,
        reference_kind: Literal["image", "video", "audio"] | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> Page[Model]:
        """Lists the models the organization can run.

        Args:
            capability: Only image or video models.
            operation: Only models with this operation, the last segment of a model ID, such
                as `edit` or `text-to-video`.
            q: Searches model IDs and labels, including the maker and related operations.
            frames: Only video models accepting at least these frame slots.
            audio: Only video models that can generate audio.
            reference_kind: Only models accepting reference media of this kind.
            limit: Models per page, up to 50; default 20.
            cursor: `next_cursor` from an earlier page, with the same filters.
        """
        return self._client._list(
            ModelList.model_validate,
            "/models",
            _query(capability, operation, q, frames, audio, reference_kind, limit, cursor),
            options,
        )

    def get(self, id: str, /, **options: Unpack[RequestOptions]) -> ModelDetail:
        """Reads a model and its request schema, by an ID such as
        `openai/gpt-image-2/generate`."""
        return self._client._request(ModelDetail.model_validate, "GET", _path(id), options=options)


class AsyncModels:
    def __init__(self, client: AsyncZeroGen) -> None:
        self._client = client

    def list(
        self,
        *,
        capability: Literal["image", "video"] | None = None,
        operation: str | None = None,
        q: str | None = None,
        frames: Literal["start", "start-end"] | None = None,
        audio: bool | None = None,
        reference_kind: Literal["image", "video", "audio"] | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> AsyncPaginator[Model]:
        """Lists the models the organization can run.

        Args:
            capability: Only image or video models.
            operation: Only models with this operation, the last segment of a model ID, such
                as `edit` or `text-to-video`.
            q: Searches model IDs and labels, including the maker and related operations.
            frames: Only video models accepting at least these frame slots.
            audio: Only video models that can generate audio.
            reference_kind: Only models accepting reference media of this kind.
            limit: Models per page, up to 50; default 20.
            cursor: `next_cursor` from an earlier page, with the same filters.
        """
        return self._client._list(
            ModelList.model_validate,
            "/models",
            _query(capability, operation, q, frames, audio, reference_kind, limit, cursor),
            options,
        )

    async def get(self, id: str, /, **options: Unpack[RequestOptions]) -> ModelDetail:
        """Reads a model and its request schema, by an ID such as
        `openai/gpt-image-2/generate`."""
        return await self._client._request(
            ModelDetail.model_validate, "GET", _path(id), options=options
        )
