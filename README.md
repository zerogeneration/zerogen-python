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

run = zerogen.runs.create_and_wait(
    {"model": "openai/gpt-image-2/generate", "prompt": "A lighthouse at dawn"}
)

for output in run.outputs:
    if output.asset:
        print(output.asset.id, output.asset.mime_type)
```

`create_and_wait` starts a run and returns it when it ends. A run that fails
returns too, so check its `status`, and each output's. Each output's asset is in
your organization's Library, in the run's project: your team can open it in
ZeroGen, you can [download it](#library), and you can send its ID as an input to
a later run. To start a run without waiting, use `create`, then `get` or
`wait_for` with its `id`.

A request body is a dict with the API's own field names, such as `projectId`
and `maxCostMicroUsd`, exactly as the
[API reference](https://docs.zerogen.com/api-reference/overview) shows it. Each
response is a pydantic model with snake_case attributes, such as
`run.project_id`. Both are typed from the API's
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
        run = await zerogen.runs.create_and_wait(
            {"model": "openai/gpt-image-2/generate", "prompt": "A lighthouse at dawn"}
        )
        print(run.status)


asyncio.run(main())
```

Cancel the task to stop a `create_and_wait` or `wait_for` from waiting; the run
keeps running.

## Inputs

Give a run an input by asset ID or by `https` URL. To upload a file, use
`uploads.upload`, which returns when the asset is ready:

```python
upload = zerogen.uploads.upload("storyboard.png")

run = zerogen.runs.create_and_wait(
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

## Library

Read and organize your organization's Library: `projects`, `assets`,
`folders`, `labels`, `naming_presets` and `skills`. These methods need an API
key with the `library:read` scope, and those that change something need
`library:organize`.

```python
project = next(project for project in zerogen.projects.list() if project.default)
videos = zerogen.assets.search(project_id=project.id, type="video", favorite=True)

folder = zerogen.folders.create(project.id, {"name": "Selects"})
zerogen.folders.add_assets(project.id, folder.id, {"assetIds": [a.id for a in videos.data]})
```

List filters that take several values, such as `label_id` and `resolution`,
take a list.

To download an asset's original file, use `assets.download`. It returns the
file's bytes, or streams them into a path or a binary file object:

```python
image = zerogen.assets.download(asset_id)
zerogen.assets.download(asset_id, "lighthouse.png")
```

Each call reads a new signed link and sends it to storage without your API key.
When storage refuses a link as expired, it reads a new one and tries once more.
To hand the link to something else, read it with `assets.get_download`: it's
valid for 5 minutes, and anyone holding it can download the file, so keep it
private.

## Previews

To show assets without downloading their originals, use their `preview`. Each
asset from `assets.search` and `assets.get` has one, and so does each run
output's `asset`.

```python
page = zerogen.assets.search(project_id=project.id, limit=50)
tiles = [
    {
        "id": asset.id,
        "image": asset.preview.image512_url if asset.preview else None,
        "clip": asset.preview.video_url if asset.preview else None,
    }
    for asset in page.data
]
```

`image96_url` and `image512_url` are WebP images up to 96 and 512 pixels wide.
`video_url` is a silent WebM clip of a video's first six seconds; it's `None`
for other assets and until the clip is made. `preview` itself is `None` until
the images are made, which can take up to about 15 minutes after a run, and for
assets with none, such as audio.

The URLs are signed storage URLs, so load them without your API key: a browser
can load one as an `<img>` element's `src`. They work until `expires_at`, 5
minutes later, and anyone holding them can load the previews until then, so
keep them out of logs. After `expires_at`, read the page again for new ones:
one `assets.search` call refreshes every tile on it, where `assets.get` would
take a request for each. For a single asset or a run, read it again.

## Lists

List methods return one page, and iterating the page reads every item on every
page after it:

```python
for model in zerogen.models.list(capability="video"):
    print(model.id)

page = zerogen.runs.list(limit=20)
print(page.data, page.next_cursor)
```

With `AsyncZeroGen`, iterate a list with `async for`, or await it for one page.

## Errors

A request the API refuses raises a `ZeroGenError`. Branch on its `code`, which
is stable; its `message` is for people.

```python
from zerogen import ZeroGenError

try:
    zerogen.runs.create({"model": "openai/gpt-image-2/generate", "prompt": ""})
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
retried create never starts a second run. To retry safely across calls or
processes, pass your own key:

```python
zerogen.runs.create(request, idempotency_key=job.id)
```

## Options

```python
import os

zerogen = ZeroGen(
    api_key=os.environ["ZEROGEN_API_KEY"],
    max_retries=2,
    timeout=120,  # Seconds per attempt. Waits on a run add their wait.
)
```

| Option | Default | Description |
| --- | --- | --- |
| `api_key` | `ZEROGEN_API_KEY` | The API key. |
| `base_url` | `ZEROGEN_BASE_URL`, then `https://api.zerogen.com/v1` | The API's base URL. |
| `max_retries` | `2` | Retries for each request. |
| `timeout` | `120` | Seconds httpx waits on each step of an attempt. A request that waits on a run gets its wait added. |
| `default_headers` | None | Headers to send with every request. |
| `http_client` | A new `httpx.Client` or `httpx.AsyncClient` | The httpx client to send requests with, such as one with your proxy settings. |

Every method also takes request options as keyword arguments: `timeout`,
`max_retries`, `headers`, and `idempotency_key` for a `POST`. Close a client
you're done with, or use it as a context manager.

## Test keys

A test key runs every request on placeholder providers and charges nothing. Its
runs can rehearse failures with the `test` field, and it reaches only the API
sandbox project. For details, see
[Test keys](https://docs.zerogen.com/test-keys).

## License

MIT
