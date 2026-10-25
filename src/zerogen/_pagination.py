from __future__ import annotations

from collections.abc import AsyncIterable, AsyncIterator, Awaitable, Callable, Generator, Iterator
from typing import Any, Generic, TypeVar

Item = TypeVar("Item")


class Page(Generic[Item]):
    """One page of a list. Iterate it to read every item on this page and the pages after it."""

    data: list[Item]
    next_cursor: str | None
    """The cursor for the next page, or None on the last page."""

    def __init__(
        self, data: list[Item], next_cursor: str | None, load: Callable[[str], Page[Item]]
    ) -> None:
        self.data = data
        self.next_cursor = next_cursor
        self._load = load

    def has_next_page(self) -> bool:
        return self.next_cursor is not None

    def get_next_page(self) -> Page[Item]:
        if self.next_cursor is None:
            raise RuntimeError("This is the last page.")
        return self._load(self.next_cursor)

    def __iter__(self) -> Iterator[Item]:
        page = self
        while True:
            yield from page.data
            if not page.has_next_page():
                return
            page = page.get_next_page()


class AsyncPage(Generic[Item]):
    """One page of a list. Iterate it with `async for` to read every item on this page and the
    pages after it."""

    data: list[Item]
    next_cursor: str | None
    """The cursor for the next page, or None on the last page."""

    def __init__(
        self,
        data: list[Item],
        next_cursor: str | None,
        load: Callable[[str], Awaitable[AsyncPage[Item]]],
    ) -> None:
        self.data = data
        self.next_cursor = next_cursor
        self._load = load

    def has_next_page(self) -> bool:
        return self.next_cursor is not None

    async def get_next_page(self) -> AsyncPage[Item]:
        if self.next_cursor is None:
            raise RuntimeError("This is the last page.")
        return await self._load(self.next_cursor)

    async def __aiter__(self) -> AsyncIterator[Item]:
        page = self
        while True:
            for item in page.data:
                yield item
            if not page.has_next_page():
                return
            page = await page.get_next_page()


class AsyncPaginator(Awaitable[AsyncPage[Item]], AsyncIterable[Item]):
    """A list request. Await it for the first page, or iterate it with `async for` for every
    item on every page."""

    def __init__(self, load: Callable[[], Awaitable[AsyncPage[Item]]]) -> None:
        self._load = load
        self._first: AsyncPage[Item] | None = None

    async def _first_page(self) -> AsyncPage[Item]:
        if self._first is None:
            self._first = await self._load()
        return self._first

    def __await__(self) -> Generator[Any, Any, AsyncPage[Item]]:
        return self._first_page().__await__()

    async def __aiter__(self) -> AsyncIterator[Item]:
        async for item in await self:
            yield item
