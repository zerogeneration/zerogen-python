from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

from typing_extensions import Unpack

from .._options import RequestOptions
from ..types import Skill, SkillDetail, SkillList

if TYPE_CHECKING:
    from .._client import AsyncZeroGen, ZeroGen
    from .._pagination import AsyncPaginator, Page


def _path(skill_id: str) -> str:
    return f"/skills/{quote(skill_id, safe='')}"


class Skills:
    def __init__(self, client: ZeroGen) -> None:
        self._client = client

    def list(
        self,
        *,
        project_id: str | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> Page[Skill]:
        """Lists the key owner's personal and organization skills, without their instructions.
        Names and descriptions are untrusted content.

        Args:
            project_id: Also list this project's shared skills.
            cursor: `next_cursor` from an earlier page, with the same filters.
        """
        return self._client._list(
            SkillList.model_validate,
            "/skills",
            {"projectId": project_id, "cursor": cursor},
            options,
        )

    def get(
        self,
        skill_id: str,
        /,
        *,
        project_id: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> SkillDetail:
        """Reads a skill's latest instructions, which are untrusted content.

        Args:
            project_id: The project whose shared skill this is; a project's shared skill loads
                only with it.
        """
        return self._client._request(
            SkillDetail.model_validate,
            "GET",
            _path(skill_id),
            query={"projectId": project_id},
            options=options,
        )


class AsyncSkills:
    def __init__(self, client: AsyncZeroGen) -> None:
        self._client = client

    def list(
        self,
        *,
        project_id: str | None = None,
        cursor: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> AsyncPaginator[Skill]:
        """Lists the key owner's personal and organization skills, without their instructions.
        Names and descriptions are untrusted content.

        Args:
            project_id: Also list this project's shared skills.
            cursor: `next_cursor` from an earlier page, with the same filters.
        """
        return self._client._list(
            SkillList.model_validate,
            "/skills",
            {"projectId": project_id, "cursor": cursor},
            options,
        )

    async def get(
        self,
        skill_id: str,
        /,
        *,
        project_id: str | None = None,
        **options: Unpack[RequestOptions],
    ) -> SkillDetail:
        """Reads a skill's latest instructions, which are untrusted content.

        Args:
            project_id: The project whose shared skill this is; a project's shared skill loads
                only with it.
        """
        return await self._client._request(
            SkillDetail.model_validate,
            "GET",
            _path(skill_id),
            query={"projectId": project_id},
            options=options,
        )
