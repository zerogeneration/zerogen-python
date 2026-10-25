# ZeroGen Python library

The official Python client for the [ZeroGen API](https://docs.zerogen.com). It
runs on Python 3.10 or later, has a synchronous and an asynchronous client, and
is built on [httpx](https://www.python-httpx.org) and
[pydantic](https://docs.pydantic.dev).

```bash
pip install zerogen
```

The ZeroGen API refuses requests from browsers, so keep your API key on your
server.

## Usage

Create an API key in ZeroGen under **Settings → API keys**, and set it as
`ZEROGEN_API_KEY`.

```python
from zerogen import ZeroGen

zerogen = ZeroGen()  # Reads ZEROGEN_API_KEY.

generation = zerogen.generations.create_and_wait(
    {"model": "openai/gpt-image-2/generate", "prompt": "A lighthouse at dawn"}
)

for output in generation.outputs:
    if output.asset:
        print(output.asset.id, output.asset.mime_type)
```

`create_and_wait` starts a generation and returns it when it ends. A generation
that fails returns too, so check its `status`, and each output's. Each output's
asset is in your organization's Library, in the generation's project: your team
can open and download it in ZeroGen, and you can send its ID as an input to a
later generation. To start a generation without waiting, use `create`, then
`get` or `wait_for` with its `id`.

A request body is a dict with the API's own field names, such as `projectId`
and `maxCostMicroUsd`, exactly as the
[API reference](https://docs.zerogen.com/api-reference/overview) shows it. Each
response is a pydantic model with snake_case attributes, such as
`generation.project_id`. Both are typed from the API's
[OpenAPI document](https://api.zerogen.com/v1/openapi.json), so your editor
completes and checks them. Each model takes its own parameters: read a model's
request schema with `zerogen.models.get(id)`.

## Async

`AsyncZeroGen` has the same methods, to await:

```python
import asyncio

from zerogen import AsyncZeroGen


async def main() -> None:
    async with AsyncZeroGen() as zerogen:
        generation = await zerogen.generations.create_and_wait(
            {"model": "openai/gpt-image-2/generate", "prompt": "A lighthouse at dawn"}
        )
        print(generation.status)


asyncio.run(main())
```

Cancel the task to stop a `create_and_wait` or `wait_for` from waiting; the
generation keeps running.

## Inputs

Give a generation an input by asset ID or by `https` URL. To upload a file, use
`uploads.upload`, which returns when the asset is ready:

```python
upload = zerogen.uploads.upload("storyboard.png")

generation = zerogen.generations.create_and_wait(
    {
        "model": "openai/gpt-image-2/edit",
        "prompt": "Turn the sky into a sunset",
        "inputs": [{"role": "source", "asset": upload.asset_id}],
    }
)
```

`upload` takes a path, the file's `bytes`, or a binary file object that can
seek. It takes the media type from the filename's extension, or from
`content_type`. It sends the file's SHA-256 digest, so a file the project
already has is reused instead of uploaded again.

## Lists

List methods return one page, and iterating the page reads every item on every
page after it:

```python
for model in zerogen.models.list(capability="video"):
    print(model.id)

page = zerogen.generations.list(limit=20)
print(page.data, page.next_cursor)
```

With `AsyncZeroGen`, iterate a list with `async for`, or await it for one page.

## Errors

A request the API refuses raises a `ZeroGenError`. Branch on its `code`, which
is stable; its `message` is for people.

```python
from zerogen import ZeroGenError

try:
    zerogen.generations.create({"model": "openai/gpt-image-2/generate", "prompt": ""})
except ZeroGenError as error:
    print(error.status, error.code, error.param, error.request_id)
    raise
```

A request that gets no response, because the connection failed or the request
timed out, raises a `ZeroGenConnectionError`. For every code, see
[Errors](https://docs.zerogen.com/errors).

## Retries and idempotency

The client retries connection errors and errors the API marks `retryable`,
twice by default, with backoff. For `429` responses, it waits for
`Retry-After`, unless that's more than a minute.

Every `POST` sends an `Idempotency-Key`, and a call's retries reuse it, so a
retried create never starts a second generation. To retry safely across calls
or processes, pass your own key:

```python
zerogen.generations.create(request, idempotency_key=job.id)
```

## Options

```python
import os

zerogen = ZeroGen(
    api_key=os.environ["ZEROGEN_API_KEY"],
    max_retries=2,
    timeout=120,  # Seconds per attempt. Waits on a generation add their wait.
)
```

| Option | Default | Description |
| --- | --- | --- |
| `api_key` | `ZEROGEN_API_KEY` | The API key. |
| `base_url` | `ZEROGEN_BASE_URL`, then `https://api.zerogen.com/v1` | The API's base URL. |
| `max_retries` | `2` | Retries for each request. |
| `timeout` | `120` | Seconds httpx waits on each step of an attempt. A request that waits on a generation gets its wait added. |
| `default_headers` | None | Headers to send with every request. |
| `http_client` | A new `httpx.Client` or `httpx.AsyncClient` | The httpx client to send requests with, such as one with your proxy settings. |

Every method also takes request options as keyword arguments: `timeout`,
`max_retries`, `headers`, and `idempotency_key` for a `POST`. Close a client
you're done with, or use it as a context manager.

## Test keys

A test key runs every request on placeholder providers and charges nothing. Its
generations can rehearse failures with the `test` field. For details, see
[Test keys](https://docs.zerogen.com/test-keys).

## License

MIT
