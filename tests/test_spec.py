"""Checks the hand-written methods against openapi.json, which generates only the types.

Each method runs with placeholder arguments on a client that records the request it would send
instead of sending it. That request must match the operation its path names in the spec: the
method, the path parameters in order, every query parameter, `Prefer: wait`, the body and
response types, and each `Literal` argument's values.
"""

from __future__ import annotations

import inspect
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from types import UnionType
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints

import httpx
import pytest

from zerogen import AsyncPage, AsyncPaginator, AsyncZeroGen, Page, ZeroGen
from zerogen._client import Query

SPEC: dict[str, Any] = json.loads(
    (Path(__file__).parent.parent / "openapi.json").read_text(encoding="utf-8")
)
COMPOSITE = {"runs.create_and_wait", "uploads.upload", "assets.download"}
"""Methods made of other methods, which this checks instead."""
UNTYPED = {"models.list operation"}
"""Arguments the spec gives an enum that the method takes as any string, because the enum
grows with each new model operation."""
HINT_NAMES = {
    "Page": Page,
    "AsyncPage": AsyncPage,
    "AsyncPaginator": AsyncPaginator,
    "ZeroGen": ZeroGen,
    "AsyncZeroGen": AsyncZeroGen,
    "Query": Query,
}


def snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


@dataclass
class Operation:
    id: str
    method: str
    path: re.Pattern[str]
    query: dict[str, dict[str, Any]]
    headers: set[str]
    body: str | None
    response: str | None


@dataclass
class Sent:
    method: str
    path: str
    query: set[str]
    waits: bool
    body: str | None
    response: str


class Captured(Exception):
    def __init__(self, sent: Sent) -> None:
        self.sent = sent


def ref_name(schema: dict[str, Any]) -> str | None:
    ref: str | None = schema.get("$ref")
    return ref.rsplit("/", 1)[-1] if ref else None


def operations() -> list[Operation]:
    shared: dict[str, Any] = SPEC["components"]["parameters"]
    found: list[Operation] = []
    for template, item in SPEC["paths"].items():
        for method in ("get", "post", "put", "patch", "delete"):
            op: dict[str, Any] | None = item.get(method)
            if op is None:
                continue
            params = [
                shared[ref_name(p) or ""] if "$ref" in p else p for p in op.get("parameters", [])
            ]
            body = op.get("requestBody", {}).get("content", {}).get("application/json", {})
            ok = [r for code, r in op["responses"].items() if code.startswith("2")]
            found.append(
                Operation(
                    id=op["operationId"],
                    method=method.upper(),
                    path=re.compile(
                        re.sub(r"\{(\w+)\}", lambda m: f"P_{snake(m.group(1))}", template)
                    ),
                    query={p["name"]: p["schema"] for p in params if p["in"] == "query"},
                    headers={p["name"] for p in params if p["in"] == "header"},
                    body=ref_name(body.get("schema", {})),
                    response=ref_name(ok[0]["content"]["application/json"]["schema"]),
                )
            )
    return found


OPERATIONS = operations()


def resources(client_class: type[Any]) -> dict[str, type[Any]]:
    return {
        name: hint
        for name, hint in get_type_hints(client_class).items()
        if getattr(hint, "__module__", "").startswith("zerogen.resources.")
    }


def methods(owner: type[Any]) -> list[str]:
    return [
        name
        for name, _ in inspect.getmembers(owner, inspect.isfunction)
        if not name.startswith("_") and name not in ("close", "aclose")
    ]


TARGETS = sorted(
    {f"{resource}.{name}" for resource, cls in resources(ZeroGen).items() for name in methods(cls)}
    | {f".{name}" for name in methods(ZeroGen)}
)


def placeholder(hint: Any) -> Any:
    origin = get_origin(hint)
    args = [arg for arg in get_args(hint) if arg is not type(None)]
    if origin is Literal:
        return args[0]
    if origin in (Union, UnionType):
        lists = [arg for arg in args if get_origin(arg) in (Sequence, list)]
        return placeholder(lists[0] if lists else args[0])
    if origin in (Sequence, list):
        return [placeholder(args[0]), placeholder(args[0])]
    return {bool: True, int: 7}.get(hint, "s")


def literal_values(hint: Any) -> set[Any] | None:
    for arg in [hint, *get_args(hint)]:
        if get_origin(arg) is Literal:
            return set(get_args(arg))
        if get_origin(arg) in (Sequence, list):
            values = literal_values(get_args(arg)[0])
            if values is not None:
                return values
    return None


def capture(client: ZeroGen | AsyncZeroGen, target: str) -> tuple[Sent, dict[str, Any]]:
    """Calls a method with placeholder arguments and returns what it would send."""
    resource, name = target.split(".")
    method = getattr(getattr(client, resource) if resource else client, name)
    hints = get_type_hints(method, localns=HINT_NAMES)
    args: list[Any] = []
    kwargs: dict[str, Any] = {}
    body: str | None = None
    for param in inspect.signature(method).parameters.values():
        if param.kind is param.VAR_KEYWORD:
            continue
        if param.name == "body":
            body = hints["body"].__name__
            args.append({})
        elif param.kind is param.POSITIONAL_ONLY:
            single = target == "models.get"
            args.append("P_vendor/P_model/P_operation" if single else f"P_{param.name}")
        else:
            kwargs[param.name] = placeholder(hints[param.name])

    def request(
        cast_to: Any,
        method: str,
        path: str,
        *,
        query: Query | None = None,
        body: object | None = None,
        wait: int | None = None,
        options: object,
    ) -> Any:
        model: str = cast_to.__self__.__name__
        names = {key for key, value in (query or {}).items() if value is not None}
        raise Captured(Sent(method, path, names, wait is not None, None, model))

    def list_(cast_to: Any, path: str, query: Query, options: object) -> Any:
        request(cast_to, "GET", path, query=query, options=options)

    client._request = request  # type: ignore[method-assign, assignment]
    client._list = list_  # type: ignore[method-assign, assignment]
    try:
        result = method(*args, **kwargs)
        if inspect.iscoroutine(result):
            result.send(None)
    except Captured as captured:
        captured.sent.body = body
        return captured.sent, {name: hints[name] for name in kwargs}
    raise AssertionError(f"{target} sent nothing")


def client(kind: str) -> ZeroGen | AsyncZeroGen:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise AssertionError("The check sends nothing.")

    if kind == "sync":
        return ZeroGen(api_key="k", http_client=httpx.Client(transport=httpx.MockTransport(refuse)))
    return AsyncZeroGen(
        api_key="k", http_client=httpx.AsyncClient(transport=httpx.MockTransport(refuse))
    )


def operation_for(sent: Sent) -> Operation:
    matches = [op for op in OPERATIONS if op.method == sent.method and op.path.fullmatch(sent.path)]
    assert len(matches) == 1, f"{sent.method} {sent.path} matches {len(matches)} operations"
    return matches[0]


@pytest.mark.parametrize("kind", ["sync", "async"])
@pytest.mark.parametrize("target", [t for t in TARGETS if t.lstrip(".") not in COMPOSITE])
def test_each_method_sends_its_operation_as_the_spec_defines_it(kind: str, target: str) -> None:
    sent, kwargs = capture(client(kind), target)
    op = operation_for(sent)
    assert sent.query == set(op.query), op.id
    assert ("wait" in kwargs) <= sent.waits <= ("Prefer" in op.headers), op.id
    assert sent.body == op.body, op.id
    assert sent.response == op.response, op.id
    if op.method == "POST":
        assert "Idempotency-Key" in op.headers, op.id
    for name, hint in kwargs.items():
        if name == "wait":
            continue
        wire = next(key for key in op.query if snake(key) == name)
        schema = op.query[wire]
        enum: list[Any] | None = schema.get("enum") or schema.get("items", {}).get("enum")
        values = literal_values(hint)
        if values is not None:
            assert values == set(enum or []), f"{op.id} {wire}"
        elif enum is not None and bool not in (hint, *get_args(hint)):
            assert f"{target} {name}" in UNTYPED, f"{op.id} {wire} takes any {hint}"


def test_every_operation_has_a_method() -> None:
    zerogen = client("sync")
    reached = {
        operation_for(capture(zerogen, target)[0]).id
        for target in TARGETS
        if target.lstrip(".") not in COMPOSITE
    }
    assert {op.id for op in OPERATIONS} - reached == set()


def test_both_clients_have_the_same_methods() -> None:
    assert resources(ZeroGen).keys() == resources(AsyncZeroGen).keys()
    for name, cls in resources(ZeroGen).items():
        other = resources(AsyncZeroGen)[name]
        assert methods(cls) == methods(other), name
        for method in methods(cls):
            sync = inspect.signature(getattr(cls, method)).parameters
            asynchronous = inspect.signature(getattr(other, method)).parameters
            assert [(p.name, p.kind, p.default) for p in sync.values()] == [
                (p.name, p.kind, p.default) for p in asynchronous.values()
            ], f"{name}.{method}"
