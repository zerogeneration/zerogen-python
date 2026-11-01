from __future__ import annotations

import inspect
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING
from urllib.parse import quote

from typing_extensions import Unpack

from .._errors import WaitCancelledError
from .._options import PostRequestOptions, RequestOptions, without_idempotency_key
from ..types import CreateRunRequest, Quote, Run, RunList

if TYPE_CHECKING:
    from .._client import AsyncZeroGen, ZeroGen
    from .._pagination import AsyncPaginator, Page

MAX_WAIT_SECONDS = 60
"""The most the API holds a response for a run to end."""
_ENDED = frozenset({"succeeded", "partial", "failed", "cancelled"})
_CANCEL_CHECK_SECONDS = 0.05


def has_ended(run: Run) -> bool:
    """Whether a run has ended: succeeded, partial, failed or cancelled."""
    return run.status in _ENDED


def _path(id: str) -> str:
    return f"/runs/{quote(id, safe='')}"


def _check_poll(poll: int) -> None:
    if not 1 <= poll <= MAX_WAIT_SECONDS:
        raise ValueError(f"poll takes 1 to {MAX_WAIT_SECONDS} seconds.")


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

    def wait_for(
        self,
        id: str,
        /,
        *,
        poll: int = MAX_WAIT_SECONDS,
        on_update: Callable[[Run], object] | None = None,
        cancel: threading.Event | None = None,
        **options: Unpack[RequestOptions],
    ) -> Run:
        """Returns a run when it ends.

        Args:
            poll: Seconds each read may wait for the run to end, from 1 to 60. The API answers
                as soon as the run ends, so a shorter `poll` only reports progress more often,
                at a request each time.
            on_update: Called with the run after each read, the last one included.
            cancel: An event that stops the wait as soon as it's set, even partway through a
                read, by raising `WaitCancelledError`. The run keeps running. A read in
                flight finishes in a background thread, and its result is dropped.
        """
        _check_poll(poll)
        while True:
            run = self._read(id, poll, cancel, options)
            if on_update is not None:
                on_update(run)
            if has_ended(run):
                return run

    def _read(
        self, id: str, poll: int, cancel: threading.Event | None, options: RequestOptions
    ) -> Run:
        """Reads the run, waiting up to `poll` seconds for it to end. With `cancel`, reads in a
        thread, so the event can stop the wait while the read is in flight."""
        if cancel is None:
            return self.get(id, wait=poll, **options)
        if cancel.is_set():
            raise WaitCancelledError(id)
        outcome: list[Run | BaseException] = []
        done = threading.Event()

        def read() -> None:
            try:
                outcome.append(self.get(id, wait=poll, **options))
            except BaseException as error:
                outcome.append(error)
            finally:
                done.set()

        threading.Thread(target=read, name=f"zerogen-wait-{id}", daemon=True).start()
        while not done.wait(_CANCEL_CHECK_SECONDS):
            if cancel.is_set():
                raise WaitCancelledError(id)
        if isinstance(outcome[0], BaseException):
            raise outcome[0]
        return outcome[0]

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

    async def wait_for(
        self,
        id: str,
        /,
        *,
        poll: int = MAX_WAIT_SECONDS,
        on_update: Callable[[Run], object] | None = None,
        **options: Unpack[RequestOptions],
    ) -> Run:
        """Returns a run when it ends. Cancel the task to stop waiting; the run keeps
        running.

        Args:
            poll: Seconds each read may wait for the run to end, from 1 to 60. The API answers
                as soon as the run ends, so a shorter `poll` only reports progress more often,
                at a request each time.
            on_update: Called with the run after each read, the last one included. When it
                returns an awaitable, such as a coroutine function's, the wait awaits it.
        """
        _check_poll(poll)
        while True:
            run = await self.get(id, wait=poll, **options)
            if on_update is not None:
                result = on_update(run)
                if inspect.isawaitable(result):
                    await result
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
