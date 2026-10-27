# Agent guidance for zerogen-python

`zerogen`, the Python client for the [ZeroGen API](https://docs.zerogen.com).
The API's [OpenAPI document](https://api.zerogen.com/v1/openapi.json) is the
contract; this library adds retries, idempotency, waiting, pagination,
uploads and downloads on top of the types generated from it.

## Rules

- `src/zerogen/types/` is generated: never edit it by hand. After the API
  changes, run `uv run scripts/generate.py --fetch`, which fetches the
  published document into `openapi.json` and regenerates the types, then
  update the methods in `src/zerogen/resources` to match. To build against a
  document that isn't published yet, put it in `openapi.json` and run
  `uv run scripts/generate.py`.
- The generator makes only the types; the methods are hand-written.
  `tests/test_spec.py` checks every method against `openapi.json` (method,
  path, query parameters, `Prefer: wait`, body and response types, `Literal`
  values) and fails until each operation has a method that matches it.
- Request bodies are TypedDicts with the API's own field names, sent as
  given. Responses are pydantic models that leave out the document's
  constraints and accept enum values and fields they don't know yet, so an
  older client keeps working when the API grows. Keep it that way.
- `ZeroGen` and `AsyncZeroGen` have the same methods. Change both. The
  `make_client` fixture runs a test once with each.
- Every `POST` sends an `Idempotency-Key` that the call's retries reuse.
  Retries follow the error's `retryable` and `Retry-After`; keep it that way.
- Signed storage URLs, for uploads and downloads, go through the client's
  `_storage` method, which sends only the headers storage needs (never the API
  key or any caller or client headers) and keeps the URL's signed query out of
  httpx's request log. A signed URL is a credential, so never put one in an
  error message or a log.
- Tests use a scripted httpx transport (`tests/fakes.py`) and never call the
  API.
- The library supports Python 3.10 and later. Before you commit, run
  `uv run scripts/check.py` (Ruff's linter and formatter, pyright, pytest).

## Releases

Maintainers publish releases:

1. Bump `version` in `pyproject.toml` and `__version__` in
   `src/zerogen/_version.py`, run `uv lock`, and add a `CHANGELOG.md` entry.
   Merge the change.
2. Publish a GitHub release whose tag is `v` plus the version, such as
   `v0.2.0`. The `Release` workflow checks the tag, runs the checks, builds the
   package, and publishes it to PyPI through trusted publishing.
