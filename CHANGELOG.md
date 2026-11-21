# Changelog

## 0.5.0

This release follows the API's new attachment contract, and breaks attachment
code written for 0.4. Nothing else changes for existing code. Its attachment
models need the fields the API added for this release, so 0.4's
`attachments.list` and `attachments.versions` can't read the new API, and
0.5 can't read an older deployment of it.

- `attachments.create` needs a `description`: one line saying what the
  attachment holds and when to read it. Lists and `get` return it.
- An attachment's and a version's `characters` is now `bytes`, the text's size
  in UTF-8 bytes. The text holds up to 64 KiB, up from 8,000 characters.
- Attachments on assets: `attachments.create` takes `assetId`,
  `attachments.list` takes `asset_id`, and a parent's `kind` can be
  `"asset"`.
- `attachments.revise` can change the `title` and the `description` as well
  as the `body`; a field left out keeps its value.
- `projects.get`, `folders.get` and `assets.get` return the resource's own
  `attachments` as `AttachmentSummary` items, without their text. Lists of
  folders and assets carry `attachment_count`. Both appear only where
  attachments are enabled.
- `runs.create` takes `layers`, for image-to-layers models.
- Types from the current API, including new models.

## 0.4.0

This release breaks compatibility with 0.3, for the API's reshaped Library and
runs. Library writes take the resource's ID alone, every list pages, and lineage
splits into sources and uses. [Migrating from 0.3](#migrating-from-03) lists
each change and what replaces it. Its models need the fields the API added for
this release, such as a run's `endedAt`, `kind` and `request`, so it can't read
an older deployment of the API.

- Waits end on the run's `ended_at`, which the API sets exactly when a run ends,
  whatever its status, so a status added later can't keep `wait_for`,
  `create_and_wait` or `transform_and_wait` waiting. `has_ended` checks
  `ended_at` too.
- Runs have `kind`, `ended_at` and `request`, what the run was asked to make in
  the create request's shape. `runs.list` lists every member's runs and takes
  `created_by`, `status`, `created_after` and `created_before`, up to 100 a page.
- `runs.get_output_download`, `runs.download_output` and
  `runs.download_output_to` download a run's output with only `runs:read`.
- `runs.quote` returns `inputs`, the assets a create would use. A quote needs
  `models:read`, not `runs:create`.
- `ZeroGenError.reason` is a `rate_limited` or `permission_denied` error's
  `details.reason`, typed as `ErrorReason`, the known reasons or any string.
- Transforms: `assets.transform` and `assets.transform_and_wait` make a free
  Derived copy of an asset from a recipe, typed as `TransformRecipe` and its
  forms `FrameRecipe`, `ImageRecipe`, `VideoRecipe` and `AudioRecipe`.
  `luts.list` lists the LUTs a recipe can name, each a `Lut`.
- `assets.delete` and `assets.restore` move an asset to Recently deleted and
  back.
- `attachments`: `list`, `get`, `create`, `revise`, `delete`, `restore` and
  `versions` for versioned text on projects, folders and Story clips.
- `projects.get`, `folders.get` and `labels.get` read one by ID, and
  `naming_presets.create` saves a preset.
- `runs.create` takes `continuation` for Nano Banana edits.
- Every `PATCH` sends an `Idempotency-Key`, as `POST` and `DELETE` do.
- An error from storage quotes only the storage error's code and message, never
  the rest of its body, which can echo the signed link.
- `uploads.upload` raises a `permission_denied` from declaring an identical file
  unless its `reason` is `not_creator`, such as a missing scope, instead of
  reporting the declaration as not recorded.

### Migrating from 0.3

| 0.3 | 0.4 |
| --- | --- |
| `assets.lineage(asset_id)`, a `Lineage` | `assets.sources(asset_id)` and `assets.uses(asset_id)`, lists of `LineageAsset`. Each item's `edges` replace `Lineage.edges`, and `more_uses` and `truncated` are gone. |
| `assets.folders(asset_id)`, an `AssetFolders` | A list of `AssetFolder`, each with `folder_id` and `path`. Iterate it, or read `.data` for one page. |
| `assets.update(project_id, asset_id, body)`, an `AssetChange` | `assets.update(asset_id, body)`, the `AssetDetail` as `assets.get` reads it. |
| `folders.create(project_id, body)` | `folders.create(body)`, with `projectId` in the body. |
| `folders.update(project_id, folder_id, body)` | `folders.update(folder_id, body)`. |
| `folders.delete(project_id, folder_id, assets=...)` | `folders.delete(folder_id, assets=...)`. |
| `folders.restore(project_id, body)` | `folders.restore(body)`. |
| `folders.add_assets`, `move_assets` and `remove_assets(project_id, folder_id, body)`, a `FolderAssetsChange` | `(folder_id, body)`, an `AssetBatchChange` with `updated_asset_ids` and `skipped_asset_ids`, and no `folder_id`. |
| `labels.add_assets` and `remove_assets(project_id, label_id, body)`, a `LabelAssetsChange` | `(label_id, body)`, an `AssetBatchChange`, for up to 100 assets in any project. `asset_ids` and `assigned` are now `updated_asset_ids` and `skipped_asset_ids`. |
| `labels.update` replaced the name, description and color, so it needed all three | It changes only the fields you send. |
| `FolderAssetsRequest` and `LabelAssetsRequest` | `AssetBatchRequest`. |
| `AssetChange`, `AssetFolders`, `AssetFoldersFolder`, `FolderAssetsChange`, `LabelAssetsChange`, `Lineage`, `LineageEdge` and `LineageTruncated` | Removed with the endpoints that returned them; see above. |
| `runs.list` listed the API key owner's runs | It lists every member's. For your own, pass `created_by=zerogen.me().user.id`. |
| `projects.list` returned every project in one page | It pages, 50 a page by default. Iterating it still reads every project; `.data` holds one page. |
| `has_ended` and waits read a run's `status` | They read `ended_at`. |
| A storage error's message quoted up to 200 characters of its body | It quotes only the storage error's code and message. |
| `uploads.upload` reported any `permission_denied` from declaring an identical file as `declaration_recorded=False` | Only one whose `reason` is `not_creator`; any other raises. |

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
  have `declared`, and uploads have `run_id`, the run that recorded the
  declaration sent with them.
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
