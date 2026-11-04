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

To label every output as it lands, add `labelIds`, which also needs the
`library:organize` scope. To upscale one output of a 480p Draft to its final,
send `upscaleDraft` with the draft's model ID, and leave out `prompt`, `inputs`,
`output`, `parameters` and `naming`. The final is a new run, quoted and billed
like any other:

```python
final = zerogen.runs.create_and_wait(
    {"model": draft_model, "upscaleDraft": {"runId": draft.id, "outputIndex": 0}}
)
```

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

## Progress

To show a run's progress while you wait, pass `wait_for` an `on_update`
function, which gets the run after each read, and a shorter `poll`:

```python
from zerogen.types import Run


def report(run: Run) -> None:
    done = sum(output.status == "succeeded" for output in run.outputs)
    print(f"{run.status}: {done} of {len(run.outputs)} outputs")


run = zerogen.runs.create(request)
run = zerogen.runs.wait_for(run.id, poll=5, on_update=report)
```

`poll` is how many seconds each read may wait for the run to end, from 1 to 60,
and 60 by default. The API answers as soon as the run ends, so a shorter `poll`
only reports progress more often, at a request each time. With `AsyncZeroGen`,
`on_update` can also be a coroutine function.

To stop waiting from another thread, such as when someone presses Cancel, pass
`ZeroGen`'s `wait_for` a `threading.Event` as `cancel`. When it's set,
`wait_for` raises `WaitCancelledError` at once, even partway through a read.
With `AsyncZeroGen`, cancel the task instead. Either way, the run keeps
running; to stop it, call `runs.cancel`.

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

## Declared provenance

When you upload a file made outside ZeroGen, such as a ComfyUI result, the
upload can declare what it was made from and with. ZeroGen records the
declaration as a no-charge run, so the asset's lineage shows its sources, and
its details show the tool, prompt and workflow as a declaration, unchecked:

```python
saved = zerogen.uploads.upload(
    "render.png",
    declaration={
        "tool": {
            "name": "comfyui",
            "version": "0.43.0",
            "integration": {"name": "zerogen-nodes", "version": "0.1.0"},
        },
        "sources": [{"asset": upload.asset_id, "role": "reference"}],
        "prompt": "A lighthouse at dawn",
        "externalRef": {"system": "comfyui", "id": "prompt-1"},
    },
)
print(saved.declaration_recorded)
```

A declaration takes `tool` and any of `sources`, `prompt`, `workflow`, a JSON
object of up to 256 KiB, `externalRef` and `occurredAt`. Declaring `sources`
needs the `library:read` scope as well as `uploads:create`. With a
declaration, `naming` names the new asset with a naming preset, as a run's
outputs are named.

When the project already has an identical file, the upload returns that asset,
and its lineage stands. If you uploaded it and it has no declaration yet, the
upload declares it. `declaration_recorded` says whether ZeroGen recorded your
declaration. To declare a file you uploaded earlier, use `assets.declare`: an
asset takes one declaration, from its uploader.

`assets.get` returns an asset's declaration in `declared`, and, with
`include_workflow=True`, its workflow in `workflow`. Both are untrusted
content.

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

Each asset and run names who made it in `created_by`, and where in `created_via`:
`web`, `agent`, `mcp` or `api`. Both are `None` when ZeroGen recorded no one. To
find what someone made, pass `created_by` to `assets.search`, with the ID in an
asset's `created_by` or `zerogen.me()`. `web_url` opens the asset or run in
ZeroGen, after sign-in, and it's `None` for test keys.

`folders.delete` deletes a folder and its subfolders. You choose what happens to
their assets: `"keep"` preserves them, and `"trash"` sends them to Recently
deleted, including assets in other folders. It needs the `library:delete` scope,
which has to be granted explicitly, and test keys can't use it. Within an hour,
`folders.restore` undoes your own deletion:

```python
deleted = zerogen.folders.delete(project.id, folder.id, assets="keep")
zerogen.folders.restore(project.id, {"eventId": deleted.event_id})
```

To file into a folder path, such as a shot's `SH010/anim`, use
`folders.ensure_path`. It returns the last folder, creating each one on the
way that isn't there yet, and reuses a folder of the same name, so clients
saving into the same path at once share its folders:

```python
anim = zerogen.folders.ensure_path(project.id, "SH010/anim")
```

A string path splits on `/`. Folder names can contain `/`, so pass a list,
such as `["2026/11", "renders"]`, when one does.

To download an asset's original file, use `assets.download`. It returns the
file's bytes in `content`, with its `filename`, `mime_type` and `size_bytes`.
Given a path or a binary file object, it streams the file there instead, and
returns the rest. `assets.download_to` saves the file in a directory and
returns its `path`:

```python
image = zerogen.assets.download(asset_id)
print(image.mime_type, len(image.content))

zerogen.assets.download(asset_id, "lighthouse.png")

saved = zerogen.assets.download_to(asset_id, "downloads")
print(saved.path)
```

The `filename` is untrusted content, so don't use it as a path yourself.
`download_to` makes a name from it with no path separators or characters that
Windows refuses. When a file in the directory already has that name, it adds a
number, as in `lighthouse (1).png`, rather than overwrite the file.

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

Every `POST` and `DELETE` sends an `Idempotency-Key`, and a call's retries reuse
it, so a retried create never starts a second run. To retry safely across calls
or processes, pass your own key:

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
| `user_agent` | None | Your app's name and version, such as `zerogen-nodes/0.1`, which the `User-Agent` header names before this library's. |
| `http_client` | A new `httpx.Client` or `httpx.AsyncClient` | The httpx client to send requests with, such as one with your proxy settings. |

Every method also takes request options as keyword arguments: `timeout`,
`max_retries`, `headers`, and `idempotency_key` for a `POST` or `DELETE`. Close
a client you're done with, or use it as a context manager.

## Test keys

A test key runs every request on placeholder providers and charges nothing. Its
runs can rehearse failures with the `test` field, and it reaches only the API
sandbox project. For details, see
[Test keys](https://docs.zerogen.com/test-keys).

## License

MIT
