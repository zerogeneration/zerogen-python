# Changelog

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
