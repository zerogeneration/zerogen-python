# Changelog

## 0.3.0

This release breaks compatibility with 0.2: `assets.download` returns a
`Download` instead of the file's bytes, which are now its `content`. Its models
also need the fields the API has added since 0.2.1, such as `createdBy` and
`declared`, so it can't read an older deployment of the API.

- Declared provenance. `uploads.upload` takes a `declaration` of what the file
  was made from and with: `tool`, and any of `sources`, `prompt`, `workflow`,
  `externalRef` and `occurredAt`. With it, `naming` names the new asset with a
  naming preset. When the project already has the file, `upload` declares
  that asset instead, if it has no declaration and you uploaded it, and
  `declaration_recorded` says whether ZeroGen recorded yours.
- `assets.declare` declares an upload that became ready without a
  declaration, once.
- Assets have `declared`, the declaration as the uploader made it, and
  `assets.get(..., include_workflow=True)` reads its `workflow`. Lineage edges
  have `declared`, and uploads have `run_id`, the run that recorded their
  declaration.
- Downloads return the file's `filename`, `mime_type` and `size_bytes`.
  `assets.download` returns a `Download`, with the bytes in `content`, or a
  `DownloadInfo` when it streams the file into a path or file object.
- `assets.download_to` saves an asset's file in a directory, under a name made
  from its filename with no path separators or characters that Windows
  refuses. It adds a number, as in `lighthouse (1).png`, rather than overwrite
  a file, and returns a `SavedDownload` with the `path`.
- `runs.wait_for` takes `poll`, the seconds each read may wait for the run to
  end, and `on_update`, which gets the run after each read. On `ZeroGen`, it
  also takes `cancel`, a `threading.Event` that stops the wait at once by
  raising `WaitCancelledError`.
- `ZeroGen` and `AsyncZeroGen` take `user_agent`, your app's name and version,
  which the `User-Agent` header names before the library's own, as in
  `zerogen-nodes/0.1 zerogen-python/0.3.0`.
- `folders.ensure_path` returns the folder at a path such as `"SH010/anim"`,
  creating each folder on the way that isn't there yet. It reuses a folder of
  the same name under the same parent, so clients saving into one path at once
  share its folders. Pass a list of names when a name contains `/`.
- `folders.create` takes `reuseExisting`: with `True`, a folder of that name
  already under the parent is returned instead of a second one.
- `runs.create` takes `seed` for models that accept one, `labelIds` to label
  every output as it lands, and `upscaleDraft` to upscale a 480p Draft output to
  its final.
- Assets and runs have `created_by` and `created_via`, who made them and where,
  and `web_url`, which opens them in ZeroGen. `assets.search` takes `created_by`.
- `folders.delete` deletes a folder and its subfolders, with `assets` set to
  `"keep"` or `"trash"`, and `folders.restore` undoes that within an hour. A
  `DELETE` sends an `Idempotency-Key`, as a `POST` does.

## 0.2.1

- Asset previews. Each asset from `assets.search` and `assets.get`, and each
  run output's `asset`, has a `preview`: an `AssetPreview` with `image96_url`,
  `image512_url`, `video_url` and `expires_at`, or `None` until the previews
  are made. The URLs are signed: load them without your API key, and read the
  page, asset or run again after `expires_at`. 0.2.0 receives the same field
  as an untyped extra.
- When storage answers with an error whose body fails to read, the client now
  closes the response, so an `http_client` whose transport frees resources on
  close no longer leaks them.

## 0.2.0

This release breaks compatibility with 0.1.0.

- Generations are now runs, as in the API: `zerogen.generations` is now
  `zerogen.runs`, with the same methods, and calls `/v1/runs`. `Generation`,
  `GenerationList` and `CreateGenerationRequest` are now `Run`, `RunList` and
  `CreateRunRequest`, and Library assets name their run in `run_id`.
- The Library: `projects.list`; `assets.search`, `get`, `lineage`, `folders`
  and `update`; `folders.list`, `create`, `update`, `add_assets`,
  `move_assets` and `remove_assets`; `labels.list`, `create`, `update`,
  `archive`, `restore`, `add_assets` and `remove_assets`;
  `naming_presets.list`; and `skills.list` and `get`.
- Downloads: `assets.get_download` reads a signed link to an asset's original
  file, and `assets.download` fetches the file as bytes or into a path or file
  object. It reads a new link for each call and again when storage refuses an
  expired one, and never sends your API key or headers to storage.
- Speech models: `models.list` takes `capability="speech"`, and a run takes a
  `voice`.
- Requests to storage, for uploads too, now carry only the headers storage
  needs, and none of the `http_client`'s headers, cookies or auth. httpx's
  request log leaves out their signed query.
- The client no longer follows redirects, even with an `http_client` that does.
  A redirect raises a `ZeroGenError` with its status.

## 0.1.0

The first release: synchronous and asynchronous clients for every `/v1`
endpoint, typed from the API's OpenAPI document, with retries, automatic
idempotency keys, `create_and_wait`, paginated lists, and file uploads.
