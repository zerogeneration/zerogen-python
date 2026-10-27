from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

from typing_extensions import Unpack

from .._options import PostRequestOptions, RequestOptions, without_idempotency_key
from ..types import CreateRunRequest, Quote, Run, RunList

if TYPE_CHECKING:
    from .._client import AsyncZeroGen, ZeroGen
    from .._pagination import AsyncPaginator, Page

MAX_WAIT_SECONDS = 60
"""The most the API holds a response for a run to end."""
_ENDED = frozenset({"succeeded", "partial", "failed", "cancelled"})


def has_ended(run: Run) -> bool:
    """Whether a run has ended: succeeded, partial, failed or cancelled."""
    return run.status in _ENDED


def _path(id: str) -> str:
    return f"/runs/{quote(id, safe='')}"


class Runs:
    def __init__(self, client: ZeroGen) -> None:
        self._client = client

    def quote(self, body: CreateRunRequest, /, **options: Unpack[PostRequestOptions]) -> Quote:
        """Prices a request without starting it."""
        return self._client._request(
            Quote.model_validate, "POST", "/runs/quote", body=body, options=options
        )

    def create(
        self,
        body: CreateRunRequest,
        /,
        *,
        wait: int | None = None,
        **options: Unpack[PostRequestOptions],
    ) -> Run:
        """Starts a run.

        Args:
            wait: Seconds the API may hold the response until the run ends, up to 60.
                Without it, the response returns at once.
        """
        return self._client._request(
            Run.model_validate,
            "POST",
            "/runs",
            body=body,
            wait=wait,
            options=options,
        )

    def create_and_wait(
        self, body: CreateRunRequest, /, **options: Unpack[PostRequestOptions]
    ) -> Run:
        """Starts a run and returns it when it ends.

        Check its `status`: a run that failed returns too.
        """
        run = self.create(body, wait=MAX_WAIT_SECONDS, **options)
        if has_ended(run):
            return run
        return self.wait_for(run.id, **without_idempotency_key(options))

    def get(self, id: str, /, *, wait: int | None = None, **options: Unpack[RequestOptions]) -> Run:
        """Reads a run.

        Args:
            wait: Seconds the API may hold the response until the run ends, up to 60.
                Without it, the response returns at once.
        """
        return self._client._request(
            Run.model_validate, "GET", _path(id), wait=wait, options=options
        )

    def wait_for(self, id: str, /, **options: Unpack[RequestOptions]) -> Run:
        """Returns a run when it ends."""
        while True:
            run = self.get(id, wait=MAX_WAIT_SECONDS, **options)
            if has_ended(run):
                return run

    def list(
        self,
        *,
        project_id: str | None = None,
        folder_id: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> Page[Run]:
        """Lists the runs of the API key's owner, newest first.

        Args:
            project_id: Only runs in this project.
            folder_id: Only runs filed in this folder; needs `project_id`.
            limit: Runs per page, up to 20; default 10.
            cursor: `next_cursor` from an earlier page, with the same filters.
        """
        return self._client._list(
            RunList.model_validate,
            "/runs",
            {"projectId": project_id, "folderId": folder_id, "limit": limit, "cursor": cursor},
            options,
        )

    def cancel(self, id: str, /, **options: Unpack[PostRequestOptions]) -> Run:
        """Stops a run's unfinished outputs. Outputs that already finished are kept and
        charged."""
        return self._client._request(
            Run.model_validate, "POST", f"{_path(id)}/cancel", options=options
        )


class AsyncRuns:
    def __init__(self, client: AsyncZeroGen) -> None:
        self._client = client

    async def quote(
        self, body: CreateRunRequest, /, **options: Unpack[PostRequestOptions]
    ) -> Quote:
        """Prices a request without starting it."""
        return await self._client._request(
            Quote.model_validate, "POST", "/runs/quote", body=body, options=options
        )

    async def create(
        self,
        body: CreateRunRequest,
        /,
        *,
        wait: int | None = None,
        **options: Unpack[PostRequestOptions],
    ) -> Run:
        """Starts a run.

        Args:
            wait: Seconds the API may hold the response until the run ends, up to 60.
                Without it, the response returns at once.
        """
        return await self._client._request(
            Run.model_validate,
            "POST",
            "/runs",
            body=body,
            wait=wait,
            options=options,
        )

    async def create_and_wait(
        self, body: CreateRunRequest, /, **options: Unpack[PostRequestOptions]
    ) -> Run:
        """Starts a run and returns it when it ends.

        Check its `status`: a run that failed returns too. Cancel the task to stop
        waiting; the run keeps running.
        """
        run = await self.create(body, wait=MAX_WAIT_SECONDS, **options)
        if has_ended(run):
            return run
        return await self.wait_for(run.id, **without_idempotency_key(options))

    async def get(
        self, id: str, /, *, wait: int | None = None, **options: Unpack[RequestOptions]
    ) -> Run:
        """Reads a run.

        Args:
            wait: Seconds the API may hold the response until the run ends, up to 60.
                Without it, the response returns at once.
        """
        return await self._client._request(
            Run.model_validate, "GET", _path(id), wait=wait, options=options
        )

    async def wait_for(self, id: str, /, **options: Unpack[RequestOptions]) -> Run:
        """Returns a run when it ends. Cancel the task to stop waiting; the run keeps
        running."""
        while True:
            run = await self.get(id, wait=MAX_WAIT_SECONDS, **options)
            if has_ended(run):
                return run

    def list(
        self,
        *,
        project_id: str | None = None,
        folder_id: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> AsyncPaginator[Run]:
        """Lists the runs of the API key's owner, newest first.

        Args:
            project_id: Only runs in this project.
            folder_id: Only runs filed in this folder; needs `project_id`.
            limit: Runs per page, up to 20; default 10.
            cursor: `next_cursor` from an earlier page, with the same filters.
        """
        return self._client._list(
            RunList.model_validate,
            "/runs",
            {"projectId": project_id, "folderId": folder_id, "limit": limit, "cursor": cursor},
            options,
        )

    async def cancel(self, id: str, /, **options: Unpack[PostRequestOptions]) -> Run:
        """Stops a run's unfinished outputs. Outputs that already finished are kept and
        charged."""
        return await self._client._request(
            Run.model_validate, "POST", f"{_path(id)}/cancel", options=options
        )
