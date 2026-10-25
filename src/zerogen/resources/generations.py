from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

from typing_extensions import Unpack

from .._options import PostRequestOptions, RequestOptions, without_idempotency_key
from ..types import CreateGenerationRequest, Generation, GenerationList, Quote

if TYPE_CHECKING:
    from .._client import AsyncZeroGen, ZeroGen
    from .._pagination import AsyncPaginator, Page

MAX_WAIT_SECONDS = 60
"""The most the API holds a response for a generation to end."""
_ENDED = frozenset({"succeeded", "partial", "failed", "cancelled"})


def has_ended(generation: Generation) -> bool:
    """Whether a generation has ended: succeeded, partial, failed or cancelled."""
    return generation.status in _ENDED


def _path(id: str) -> str:
    return f"/generations/{quote(id, safe='')}"


class Generations:
    def __init__(self, client: ZeroGen) -> None:
        self._client = client

    def quote(
        self, body: CreateGenerationRequest, /, **options: Unpack[PostRequestOptions]
    ) -> Quote:
        """Prices a request without starting it."""
        return self._client._request(
            Quote.model_validate, "POST", "/generations/quote", body=body, options=options
        )

    def create(
        self,
        body: CreateGenerationRequest,
        /,
        *,
        wait: int | None = None,
        **options: Unpack[PostRequestOptions],
    ) -> Generation:
        """Starts a generation.

        Args:
            wait: Seconds the API may hold the response until the generation ends, up to 60.
                Without it, the response returns at once.
        """
        return self._client._request(
            Generation.model_validate,
            "POST",
            "/generations",
            body=body,
            wait=wait,
            options=options,
        )

    def create_and_wait(
        self, body: CreateGenerationRequest, /, **options: Unpack[PostRequestOptions]
    ) -> Generation:
        """Starts a generation and returns it when it ends.

        Check its `status`: a generation that failed returns too.
        """
        generation = self.create(body, wait=MAX_WAIT_SECONDS, **options)
        if has_ended(generation):
            return generation
        return self.wait_for(generation.id, **without_idempotency_key(options))

    def get(
        self, id: str, /, *, wait: int | None = None, **options: Unpack[RequestOptions]
    ) -> Generation:
        """Reads a generation.

        Args:
            wait: Seconds the API may hold the response until the generation ends, up to 60.
                Without it, the response returns at once.
        """
        return self._client._request(
            Generation.model_validate, "GET", _path(id), wait=wait, options=options
        )

    def wait_for(self, id: str, /, **options: Unpack[RequestOptions]) -> Generation:
        """Returns a generation when it ends."""
        while True:
            generation = self.get(id, wait=MAX_WAIT_SECONDS, **options)
            if has_ended(generation):
                return generation

    def list(
        self,
        *,
        project_id: str | None = None,
        folder_id: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> Page[Generation]:
        """Lists the generations of the API key's owner, newest first.

        Args:
            project_id: Only generations in this project.
            folder_id: Only generations filed in this folder; needs `project_id`.
            limit: Generations per page, up to 20; default 10.
            cursor: `next_cursor` from an earlier page, with the same filters.
        """
        return self._client._list(
            GenerationList.model_validate,
            "/generations",
            {"projectId": project_id, "folderId": folder_id, "limit": limit, "cursor": cursor},
            options,
        )

    def cancel(self, id: str, /, **options: Unpack[PostRequestOptions]) -> Generation:
        """Stops a generation's unfinished outputs. Outputs that already finished are kept and
        charged."""
        return self._client._request(
            Generation.model_validate, "POST", f"{_path(id)}/cancel", options=options
        )


class AsyncGenerations:
    def __init__(self, client: AsyncZeroGen) -> None:
        self._client = client

    async def quote(
        self, body: CreateGenerationRequest, /, **options: Unpack[PostRequestOptions]
    ) -> Quote:
        """Prices a request without starting it."""
        return await self._client._request(
            Quote.model_validate, "POST", "/generations/quote", body=body, options=options
        )

    async def create(
        self,
        body: CreateGenerationRequest,
        /,
        *,
        wait: int | None = None,
        **options: Unpack[PostRequestOptions],
    ) -> Generation:
        """Starts a generation.

        Args:
            wait: Seconds the API may hold the response until the generation ends, up to 60.
                Without it, the response returns at once.
        """
        return await self._client._request(
            Generation.model_validate,
            "POST",
            "/generations",
            body=body,
            wait=wait,
            options=options,
        )

    async def create_and_wait(
        self, body: CreateGenerationRequest, /, **options: Unpack[PostRequestOptions]
    ) -> Generation:
        """Starts a generation and returns it when it ends.

        Check its `status`: a generation that failed returns too. Cancel the task to stop
        waiting; the generation keeps running.
        """
        generation = await self.create(body, wait=MAX_WAIT_SECONDS, **options)
        if has_ended(generation):
            return generation
        return await self.wait_for(generation.id, **without_idempotency_key(options))

    async def get(
        self, id: str, /, *, wait: int | None = None, **options: Unpack[RequestOptions]
    ) -> Generation:
        """Reads a generation.

        Args:
            wait: Seconds the API may hold the response until the generation ends, up to 60.
                Without it, the response returns at once.
        """
        return await self._client._request(
            Generation.model_validate, "GET", _path(id), wait=wait, options=options
        )

    async def wait_for(self, id: str, /, **options: Unpack[RequestOptions]) -> Generation:
        """Returns a generation when it ends. Cancel the task to stop waiting; the generation
        keeps running."""
        while True:
            generation = await self.get(id, wait=MAX_WAIT_SECONDS, **options)
            if has_ended(generation):
                return generation

    def list(
        self,
        *,
        project_id: str | None = None,
        folder_id: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> AsyncPaginator[Generation]:
        """Lists the generations of the API key's owner, newest first.

        Args:
            project_id: Only generations in this project.
            folder_id: Only generations filed in this folder; needs `project_id`.
            limit: Generations per page, up to 20; default 10.
            cursor: `next_cursor` from an earlier page, with the same filters.
        """
        return self._client._list(
            GenerationList.model_validate,
            "/generations",
            {"projectId": project_id, "folderId": folder_id, "limit": limit, "cursor": cursor},
            options,
        )

    async def cancel(self, id: str, /, **options: Unpack[PostRequestOptions]) -> Generation:
        """Stops a generation's unfinished outputs. Outputs that already finished are kept and
        charged."""
        return await self._client._request(
            Generation.model_validate, "POST", f"{_path(id)}/cancel", options=options
        )
