from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

from typing_extensions import Unpack

from .._options import RequestOptions
from ..types import Project, ProjectList

if TYPE_CHECKING:
    from .._client import AsyncZeroGen, ZeroGen
    from .._pagination import AsyncPaginator, Page


def _path(project_id: str) -> str:
    return f"/projects/{quote(project_id, safe='')}"


class Projects:
    def __init__(self, client: ZeroGen) -> None:
        self._client = client

    def list(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> Page[Project]:
        """Lists the organization's projects, the default project first, then newest first. A
        test key lists only its API sandbox.

        Args:
            limit: Projects per page, up to 100; default 50.
            cursor: `next_cursor` from an earlier page.
        """
        return self._client._list(
            ProjectList.model_validate, "/projects", {"limit": limit, "cursor": cursor}, options
        )

    def get(self, project_id: str, /, **options: Unpack[RequestOptions]) -> Project:
        """Reads a project, as the list shows it. A test key reads only its API sandbox."""
        return self._client._request(
            Project.model_validate, "GET", _path(project_id), options=options
        )


class AsyncProjects:
    def __init__(self, client: AsyncZeroGen) -> None:
        self._client = client

    def list(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> AsyncPaginator[Project]:
        """Lists the organization's projects, the default project first, then newest first. A
        test key lists only its API sandbox.

        Args:
            limit: Projects per page, up to 100; default 50.
            cursor: `next_cursor` from an earlier page.
        """
        return self._client._list(
            ProjectList.model_validate, "/projects", {"limit": limit, "cursor": cursor}, options
        )

    async def get(self, project_id: str, /, **options: Unpack[RequestOptions]) -> Project:
        """Reads a project, as the list shows it. A test key reads only its API sandbox."""
        return await self._client._request(
            Project.model_validate, "GET", _path(project_id), options=options
        )
