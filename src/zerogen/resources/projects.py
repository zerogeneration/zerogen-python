from __future__ import annotations

from typing import TYPE_CHECKING

from typing_extensions import Unpack

from .._options import RequestOptions
from ..types import Project, ProjectList

if TYPE_CHECKING:
    from .._client import AsyncZeroGen, ZeroGen
    from .._pagination import AsyncPaginator, Page


class Projects:
    def __init__(self, client: ZeroGen) -> None:
        self._client = client

    def list(self, **options: Unpack[RequestOptions]) -> Page[Project]:
        """Lists the organization's projects, in one page. A test key lists only its API
        sandbox."""
        return self._client._list(ProjectList.model_validate, "/projects", {}, options)


class AsyncProjects:
    def __init__(self, client: AsyncZeroGen) -> None:
        self._client = client

    def list(self, **options: Unpack[RequestOptions]) -> AsyncPaginator[Project]:
        """Lists the organization's projects, in one page. A test key lists only its API
        sandbox."""
        return self._client._list(ProjectList.model_validate, "/projects", {}, options)
