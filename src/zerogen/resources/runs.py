from __future__ import annotations

import inspect
import os
import threading
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import TYPE_CHECKING, Literal, overload
from urllib.parse import quote

from typing_extensions import Unpack

from .._errors import WaitCancelledError
from .._options import PostRequestOptions, RequestOptions, without_idempotency_key
from ..types import AssetDownload, CreateRunRequest, Quote, Run, RunList, TransformRun
from . import _downloads
from ._downloads import Download, DownloadDestination, DownloadInfo, SavedDownload

if TYPE_CHECKING:
    from .._client import AsyncZeroGen, Query, ZeroGen
    from .._pagination import AsyncPaginator, Page

MAX_WAIT_SECONDS = 60
"""The most the API holds a response for a run to end."""
_CANCEL_CHECK_SECONDS = 0.05

RunStatus = Literal["queued", "running", "succeeded", "partial", "failed", "cancelled"]


def has_ended(run: Run | TransformRun) -> bool:
    """Whether a run has ended, whatever its status: the API sets `ended_at` exactly when it
    has. Check each output whatever the status, since a failed or cancelled run can still hold
    succeeded outputs."""
    return run.ended_at is not None


def _path(id: str) -> str:
    return f"/runs/{quote(id, safe='')}"


def _output_download_path(id: str, asset_id: str) -> str:
    return f"{_path(id)}/outputs/{quote(asset_id, safe='')}/download"


def _check_poll(poll: int) -> None:
    if not 1 <= poll <= MAX_WAIT_SECONDS:
        raise ValueError(f"poll takes 1 to {MAX_WAIT_SECONDS} seconds.")


def _values(value: str | Sequence[str] | None) -> list[str] | None:
    if value is None:
        return None
    return [value] if isinstance(value, str) else list(value)


def _time(value: str | datetime | None) -> str | None:
    """An RFC 3339 time: a string as it is, or a datetime that knows its time zone."""
    if not isinstance(value, datetime):
        return value
    if value.utcoffset() is None:
        raise ValueError("Pass a datetime with a time zone, such as datetime.now(timezone.utc).")
    return value.isoformat()


def _list_query(
    project_id: str | None,
    folder_id: str | None,
    created_by: str | Sequence[str] | None,
    status: RunStatus | Sequence[RunStatus] | None,
    created_after: str | datetime | None,
    created_before: str | datetime | None,
    limit: int | None,
    cursor: str | None,
) -> Query:
    return {
        "projectId": project_id,
        "folderId": folder_id,
        "createdBy": _values(created_by),
        "status": _values(status),
        "createdAfter": _time(created_after),
        "createdBefore": _time(created_before),
        "limit": limit,
        "cursor": cursor,
    }


class Runs:
    def __init__(self, client: ZeroGen) -> None:
        self._client = client

    def quote(self, body: CreateRunRequest, /, **options: Unpack[PostRequestOptions]) -> Quote:
        """Prices a request without starting it, and returns the inputs a create would use.
        Needs `models:read`, not `runs:create`. Send the quote's `inputs` with the create so it
        reuses the assets the quote imported from `https` URLs."""
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

        Check its `status` and each output's: a run that failed returns too.
        """
        run = self.create(body, wait=MAX_WAIT_SECONDS, **options)
        if has_ended(run):
            return run
        return self.wait_for(run.id, **without_idempotency_key(options))

    def get(self, id: str, /, *, wait: int | None = None, **options: Unpack[RequestOptions]) -> Run:
        """Reads any run in the organization.

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
        """Returns a run when it ends, which its `ended_at` says, whatever its status.

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
        created_by: str | Sequence[str] | None = None,
        status: RunStatus | Sequence[RunStatus] | None = None,
        created_after: str | datetime | None = None,
        created_before: str | datetime | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> Page[Run]:
        """Lists the organization's runs, whoever started them, newest first. A test key lists
        its sandbox's runs.

        Args:
            project_id: Only runs in this project.
            folder_id: Only runs filed in this folder; needs `project_id`.
            created_by: Only runs any of these users started, by the ID in a run's
                `created_by` or `me()`.
            status: Only runs with any of these statuses.
            created_after: Only runs created at or after this time: an RFC 3339 string, such
                as `"2026-11-10T00:00:00Z"`, or a datetime with a time zone.
            created_before: Only runs created before this time.
            limit: Runs per page, up to 100; default 10.
            cursor: `next_cursor` from an earlier page, with the same filters.
        """
        return self._client._list(
            RunList.model_validate,
            "/runs",
            _list_query(
                project_id,
                folder_id,
                created_by,
                status,
                created_after,
                created_before,
                limit,
                cursor,
            ),
            options,
        )

    def cancel(self, id: str, /, **options: Unpack[PostRequestOptions]) -> Run:
        """Stops a run's unfinished outputs. Outputs that already finished are kept and
        charged. An output its provider already started can't be stopped: the run stays
        `running`, and that output is delivered and charged when it finishes. You can cancel
        the runs you started; an owner or admin can cancel any."""
        return self._client._request(
            Run.model_validate, "POST", f"{_path(id)}/cancel", options=options
        )

    def get_output_download(
        self, id: str, asset_id: str, /, **options: Unpack[RequestOptions]
    ) -> AssetDownload:
        """Reads a signed link to a succeeded output's original file, by the run's ID and the
        output's `asset.id`, with its filename, media type and size. Needs only `runs:read`.
        The link is valid for 5 minutes, and anyone holding it can download the file, so keep
        it private. To fetch the file, use `download_output`."""
        return self._client._request(
            AssetDownload.model_validate,
            "GET",
            _output_download_path(id, asset_id),
            options=options,
        )

    @overload
    def download_output(
        self, id: str, asset_id: str, /, **options: Unpack[RequestOptions]
    ) -> Download: ...

    @overload
    def download_output(
        self,
        id: str,
        asset_id: str,
        /,
        destination: DownloadDestination,
        **options: Unpack[RequestOptions],
    ) -> DownloadInfo: ...

    def download_output(
        self,
        id: str,
        asset_id: str,
        /,
        destination: DownloadDestination | None = None,
        **options: Unpack[RequestOptions],
    ) -> Download | DownloadInfo:
        """Downloads a succeeded output's original file, as `assets.download` does, with only
        `runs:read`. Returns a `Download` with its bytes, or streams them into `destination`
        and returns a `DownloadInfo`.

        Args:
            destination: A path, which is removed again if the download fails partway, or a
                binary file object open for writing.
        """
        return _downloads.download(
            self._client,
            lambda: self.get_output_download(id, asset_id, **options),
            destination,
            options,
        )

    def download_output_to(
        self,
        id: str,
        asset_id: str,
        directory: str | os.PathLike[str],
        /,
        **options: Unpack[RequestOptions],
    ) -> SavedDownload:
        """Downloads a succeeded output's original file into `directory`, as
        `assets.download_to` does, with only `runs:read`, and returns where it saved it."""
        return _downloads.download_to(
            self._client,
            lambda: self.get_output_download(id, asset_id, **options),
            directory,
            options,
        )


class AsyncRuns:
    def __init__(self, client: AsyncZeroGen) -> None:
        self._client = client

    async def quote(
        self, body: CreateRunRequest, /, **options: Unpack[PostRequestOptions]
    ) -> Quote:
        """Prices a request without starting it, and returns the inputs a create would use.
        Needs `models:read`, not `runs:create`. Send the quote's `inputs` with the create so it
        reuses the assets the quote imported from `https` URLs."""
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

        Check its `status` and each output's: a run that failed returns too. Cancel the task
        to stop waiting; the run keeps running.
        """
        run = await self.create(body, wait=MAX_WAIT_SECONDS, **options)
        if has_ended(run):
            return run
        return await self.wait_for(run.id, **without_idempotency_key(options))

    async def get(
        self, id: str, /, *, wait: int | None = None, **options: Unpack[RequestOptions]
    ) -> Run:
        """Reads any run in the organization.

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
        """Returns a run when it ends, which its `ended_at` says, whatever its status. Cancel
        the task to stop waiting; the run keeps running.

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
        created_by: str | Sequence[str] | None = None,
        status: RunStatus | Sequence[RunStatus] | None = None,
        created_after: str | datetime | None = None,
        created_before: str | datetime | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> AsyncPaginator[Run]:
        """Lists the organization's runs, whoever started them, newest first. A test key lists
        its sandbox's runs.

        Args:
            project_id: Only runs in this project.
            folder_id: Only runs filed in this folder; needs `project_id`.
            created_by: Only runs any of these users started, by the ID in a run's
                `created_by` or `me()`.
            status: Only runs with any of these statuses.
            created_after: Only runs created at or after this time: an RFC 3339 string, such
                as `"2026-11-10T00:00:00Z"`, or a datetime with a time zone.
            created_before: Only runs created before this time.
            limit: Runs per page, up to 100; default 10.
            cursor: `next_cursor` from an earlier page, with the same filters.
        """
        return self._client._list(
            RunList.model_validate,
            "/runs",
            _list_query(
                project_id,
                folder_id,
                created_by,
                status,
                created_after,
                created_before,
                limit,
                cursor,
            ),
            options,
        )

    async def cancel(self, id: str, /, **options: Unpack[PostRequestOptions]) -> Run:
        """Stops a run's unfinished outputs. Outputs that already finished are kept and
        charged. An output its provider already started can't be stopped: the run stays
        `running`, and that output is delivered and charged when it finishes. You can cancel
        the runs you started; an owner or admin can cancel any."""
        return await self._client._request(
            Run.model_validate, "POST", f"{_path(id)}/cancel", options=options
        )

    async def get_output_download(
        self, id: str, asset_id: str, /, **options: Unpack[RequestOptions]
    ) -> AssetDownload:
        """Reads a signed link to a succeeded output's original file, by the run's ID and the
        output's `asset.id`, with its filename, media type and size. Needs only `runs:read`.
        The link is valid for 5 minutes, and anyone holding it can download the file, so keep
        it private. To fetch the file, use `download_output`."""
        return await self._client._request(
            AssetDownload.model_validate,
            "GET",
            _output_download_path(id, asset_id),
            options=options,
        )

    @overload
    async def download_output(
        self, id: str, asset_id: str, /, **options: Unpack[RequestOptions]
    ) -> Download: ...

    @overload
    async def download_output(
        self,
        id: str,
        asset_id: str,
        /,
        destination: DownloadDestination,
        **options: Unpack[RequestOptions],
    ) -> DownloadInfo: ...

    async def download_output(
        self,
        id: str,
        asset_id: str,
        /,
        destination: DownloadDestination | None = None,
        **options: Unpack[RequestOptions],
    ) -> Download | DownloadInfo:
        """Downloads a succeeded output's original file, as `assets.download` does, with only
        `runs:read`. Returns a `Download` with its bytes, or streams them into `destination`
        and returns a `DownloadInfo`.

        Args:
            destination: A path, which is removed again if the download fails partway, or a
                binary file object open for writing, written to in a worker thread.
        """
        return await _downloads.async_download(
            self._client,
            lambda: self.get_output_download(id, asset_id, **options),
            destination,
            options,
        )

    async def download_output_to(
        self,
        id: str,
        asset_id: str,
        directory: str | os.PathLike[str],
        /,
        **options: Unpack[RequestOptions],
    ) -> SavedDownload:
        """Downloads a succeeded output's original file into `directory`, as
        `assets.download_to` does, with only `runs:read`, and returns where it saved it."""
        return await _downloads.async_download_to(
            self._client,
            lambda: self.get_output_download(id, asset_id, **options),
            directory,
            options,
        )
