# Generated from openapi.json by scripts/generate.py. Don't edit it by hand.

from __future__ import annotations

from typing import Any, Dict, Literal
from datetime import datetime
from pydantic import ConfigDict, Field
from zerogen._models import BaseModel


class MeApiKey(BaseModel):
    id: str
    name: str
    mode: Literal["live", "test"] | str
    """
    test keys run on placeholder providers, charge nothing and stay in the sandbox
    """
    scopes: list[str]
    """
    What this key can do now: its scopes that its owner's role still allows
    """
    created_at: datetime = Field(..., alias="createdAt")
    expires_at: datetime | None = Field(..., alias="expiresAt")
    """
    When the key stops working; null for never
    """


class MeOrganization(BaseModel):
    id: str
    name: str


class MeUser(BaseModel):
    id: str


class MeSandbox(BaseModel):
    project_id: str = Field(..., alias="projectId")


class Me(BaseModel):
    api_key: MeApiKey = Field(..., alias="apiKey")
    organization: MeOrganization
    user: MeUser
    """
    The key's owner, whom it acts as
    """
    sandbox: MeSandbox | None
    """
    Test keys only: the project every request of the key is confined to
    """


class BalanceLimitsOrganizationMonthly(BaseModel):
    limit_micro_usd: int | None = Field(..., alias="limitMicroUsd")
    spent_micro_usd: int = Field(..., alias="spentMicroUsd")
    """
    This UTC month's spend, as admission counts it
    """
    enforced: bool


class BalanceLimitsProjectMonthly(BaseModel):
    limit_micro_usd: int | None = Field(..., alias="limitMicroUsd")
    spent_micro_usd: int = Field(..., alias="spentMicroUsd")


class BalanceLimits(BaseModel):
    organization_monthly: BalanceLimitsOrganizationMonthly | None = Field(
        ..., alias="organizationMonthly"
    )
    project_monthly: BalanceLimitsProjectMonthly | None = Field(..., alias="projectMonthly")
    """
    With projectId, that project's monthly budget
    """


class Balance(BaseModel):
    currency: Literal["USD"] | str
    balance_micro_usd: int = Field(..., alias="balanceMicroUsd")
    held_micro_usd: int | None = Field(..., alias="heldMicroUsd")
    """
    Reserved for runs that have not settled; a hold is not a charge
    """
    available_micro_usd: int = Field(..., alias="availableMicroUsd")
    """
    What a new run's quote must fit within; it can be negative
    """
    unlimited: bool
    """
    The funds check is bypassed; usage is still charged
    """
    limits: BalanceLimits


class Model(BaseModel):
    id: str
    name: str
    capability: Literal["image", "video", "speech"] | str
    operation: (
        Literal[
            "generate",
            "edit",
            "inpaint",
            "remix",
            "text-to-vector",
            "image-to-matte",
            "image-to-layers",
            "text-to-video",
            "image-to-video",
            "first-last-frame-to-video",
            "keyframes-to-video",
            "reference-to-video",
            "audio-to-video",
            "video-to-video",
            "video-to-matte",
            "extend-video",
            "upscale-video",
            "motion-control",
            "lip-sync",
            "clean-plate",
            "render-to-real",
            "hdr",
            "outpaint",
            "reference-video-to-video",
            "text-to-speech",
        ]
        | str
    )
    status: Literal["active", "deprecated"] | str
    sunset_at: datetime | None = Field(..., alias="sunsetAt")
    """
    A deprecated model refuses new requests from this time
    """


class ModelList(BaseModel):
    data: list[Model]
    next_cursor: str | None = Field(..., alias="nextCursor")
    """
    Pass as cursor for the next page of models; null on the last page
    """


class ModelDetail(BaseModel):
    id: str
    name: str
    capability: Literal["image", "video", "speech"] | str
    operation: (
        Literal[
            "generate",
            "edit",
            "inpaint",
            "remix",
            "text-to-vector",
            "image-to-matte",
            "image-to-layers",
            "text-to-video",
            "image-to-video",
            "first-last-frame-to-video",
            "keyframes-to-video",
            "reference-to-video",
            "audio-to-video",
            "video-to-video",
            "video-to-matte",
            "extend-video",
            "upscale-video",
            "motion-control",
            "lip-sync",
            "clean-plate",
            "render-to-real",
            "hdr",
            "outpaint",
            "reference-video-to-video",
            "text-to-speech",
        ]
        | str
    )
    status: Literal["active", "deprecated"] | str
    sunset_at: datetime | None = Field(..., alias="sunsetAt")
    """
    A deprecated model refuses new requests from this time
    """
    request_schema: dict[str, Any] = Field(..., alias="requestSchema")
    """
    JSON Schema (2020-12) for POST /v1/runs with this model; x-roles lists each input role's accepted media and limits
    """


class QuoteInput(BaseModel):
    role: (
        Literal[
            "source", "reference", "face-reference", "start-frame", "end-frame", "keyframe", "mask"
        ]
        | str
    )
    asset: str
    """
    Library asset ID
    """
    time_seconds: float | None = Field(None, alias="timeSeconds")
    """
    Keyframes only, and required for them: seconds from the start of the video, on one of the model's frames
    """


class QuoteBilling(BaseModel):
    mode: Literal["platform", "byok", "test"] | str
    quoted_micro_usd: int = Field(..., alias="quotedMicroUsd")
    """
    Reserved maximum expected charge
    """


class Quote(BaseModel):
    model: str
    inputs: list[QuoteInput]
    """
    The request's inputs in order, each as the Library asset create would use: a url input's asset is the one ZeroGen imported for this quote. Send these as the create's inputs so it doesn't import the URLs again. Empty when the request has none
    """
    billing: QuoteBilling


class RunOutputWarning(BaseModel):
    code: str
    message: str


class RunOutputDraft(BaseModel):
    expires_at: datetime = Field(..., alias="expiresAt")
    """
    When upscaling this output closes
    """
    upscalable: bool
    """
    A final can be requested now: unexpired, with no final in progress
    """
    upscale: Literal["upscaling", "upscaled"] | str | None
    """
    The newest final's state, or null when none was requested
    """
    final_resolution: str | None = Field(None, alias="finalResolution")
    """
    That final's resolution, one the model's draft control lists
    """
    final_asset_id: str | None = Field(None, alias="finalAssetId")
    """
    The newest finished final's asset
    """


class RunBillingHold(BaseModel):
    state: Literal["running", "ended", "needs_attention"] | str
    """
    running: the run has not ended; ended: it ended and the hold is still pending; needs_attention: it has stayed pending 30 minutes after ending, or 24 hours after admission with no end recorded (endedAt then stays null), so ZeroGen is looking into it
    """
    ended_at: datetime | None = Field(..., alias="endedAt")
    """
    When the run ended; null while it runs or when no end was recorded
    """


class RunBilling(BaseModel):
    mode: Literal["platform", "byok", "test"] | str
    state: Literal["held", "charged", "released"] | str | None
    """
    held: an amount is reserved and nothing is charged yet; charged: chargedMicroUsd is the final charge; released: the hold ended with no charge; null: billing never admitted the run, so nothing was held or charged
    """
    hold: RunBillingHold | None = None
    """
    While held, where the run stands. It reports facts, not what settlement will do
    """
    quoted_micro_usd: int | None = Field(..., alias="quotedMicroUsd")
    """
    Reserved maximum expected charge
    """
    held_micro_usd: int | None = Field(..., alias="heldMicroUsd")
    """
    While held, the amount reserved now; it is never a charge
    """
    charged_micro_usd: int | None = Field(..., alias="chargedMicroUsd")
    """
    The final charge once charged, zero once released; it can rarely exceed the quote
    """


class RunRequestInput(BaseModel):
    role: (
        Literal[
            "source", "reference", "face-reference", "start-frame", "end-frame", "keyframe", "mask"
        ]
        | str
    )
    asset: str
    """
    Library asset ID
    """
    time_seconds: float | None = Field(None, alias="timeSeconds")
    """
    Keyframes only, and required for them: seconds from the start of the video, on one of the model's frames
    """


class RunRequestOutput(BaseModel):
    count: int | None = None
    size: str | None = None
    """
    Image size: auto or WIDTHxHEIGHT in pixels, such as 1024x1536
    """
    quality: str | None = None
    background: str | None = None
    format: Literal["png", "jpeg", "webp"] | str | None = None
    aspect_ratio: str | None = Field(None, alias="aspectRatio")
    resolution: str | None = None
    duration_seconds: float | None = Field(None, alias="durationSeconds")
    include_audio: bool | None = Field(None, alias="includeAudio")


class RunRequestLayers(BaseModel):
    max: int | None = None
    """
    The most layers to return, the base layer included
    """
    text_recognition: bool | None = Field(None, alias="textRecognition")
    """
    Also read each plain text layer's text, lines and approximate style
    """


class RunRequestUpscaleDraft(BaseModel):
    run_id: str = Field(..., alias="runId")
    output_index: int = Field(..., alias="outputIndex")
    resolution: str | None = None


class RunRequest(BaseModel):
    model: str | None
    prompt: str | None = None
    """
    Untrusted content
    """
    inputs: list[RunRequestInput] | None = None
    output: RunRequestOutput | None = None
    voice: str | None = None
    """
    Speech models only: the voice to read the prompt in, from the model's voices
    """
    parameters: dict[str, str | float | bool] | None = None
    """
    Only the parameters the model's schema lists
    """
    seed: int | None = None
    continuation: Literal["auto", "none"] | str | None = None
    """
    Nano Banana edits of their own outputs continue that conversation; none sends the image alone
    """
    layers: RunRequestLayers | None = None
    """
    Only for image-to-layers models: each output is a layer, the base first, and the quote holds max of them
    """
    upscale_draft: RunRequestUpscaleDraft | None = Field(None, alias="upscaleDraft")
    """
    For a final, the draft output it upscaled, in place of the draft's settings
    """


class AssetDeclarationAssetLabel(BaseModel):
    id: str
    name: str


class AssetDeclarationAssetDeclaredToolIntegration(BaseModel):
    name: str
    version: str | None = None


class AssetDeclarationAssetDeclaredTool(BaseModel):
    name: str
    version: str | None = None
    integration: AssetDeclarationAssetDeclaredToolIntegration | None = None
    models: list[str] | None = None


class AssetDeclarationAssetDeclaredExternalRef(BaseModel):
    system: str
    id: str


class AssetDeclarationAssetDeclared(BaseModel):
    tool: AssetDeclarationAssetDeclaredTool
    external_ref: AssetDeclarationAssetDeclaredExternalRef | None = Field(None, alias="externalRef")
    occurred_at: datetime | None = Field(None, alias="occurredAt")


class UploadUpload(BaseModel):
    method: Literal["PUT"] | str
    url: str
    headers: dict[str, str]
    expires_at: datetime = Field(..., alias="expiresAt")


class UploadFolder(BaseModel):
    id: str
    filed: bool
    error: str | None = None


class Upload(BaseModel):
    id: str
    """
    The upload's ID, which completes it
    """
    project_id: str = Field(..., alias="projectId")
    run_id: str | None = Field(..., alias="runId")
    """
    The declared upload's run, or null when none was created
    """
    status: Literal["upload_required", "ready"] | str
    """
    upload_required: PUT the bytes, then complete; ready: the asset can be used
    """
    asset_id: str | None = Field(..., alias="assetId")
    """
    Once ready, the Library asset to send as a run input; an identical file already in the project is reused
    """
    upload: UploadUpload | None
    """
    Where to PUT the file's exact bytes, with these headers, before expiresAt
    """
    folder: UploadFolder | None = None
    """
    Whether the asset was added to the folder named at create
    """


class AssetLabel(BaseModel):
    id: str
    name: str


class AssetDeclaredToolIntegration(BaseModel):
    name: str
    version: str | None = None


class AssetDeclaredTool(BaseModel):
    name: str
    version: str | None = None
    integration: AssetDeclaredToolIntegration | None = None
    models: list[str] | None = None


class AssetDeclaredExternalRef(BaseModel):
    system: str
    id: str


class AssetDeclared(BaseModel):
    tool: AssetDeclaredTool
    external_ref: AssetDeclaredExternalRef | None = Field(None, alias="externalRef")
    occurred_at: datetime | None = Field(None, alias="occurredAt")


class AssetDetailLabel(BaseModel):
    id: str
    name: str


class AssetDetailDeclaredToolIntegration(BaseModel):
    name: str
    version: str | None = None


class AssetDetailDeclaredTool(BaseModel):
    name: str
    version: str | None = None
    integration: AssetDetailDeclaredToolIntegration | None = None
    models: list[str] | None = None


class AssetDetailDeclaredExternalRef(BaseModel):
    system: str
    id: str


class AssetDetailDeclared(BaseModel):
    tool: AssetDetailDeclaredTool
    external_ref: AssetDetailDeclaredExternalRef | None = Field(None, alias="externalRef")
    occurred_at: datetime | None = Field(None, alias="occurredAt")


class AssetPreview(BaseModel):
    image96_url: str = Field(..., alias="image96Url")
    """
    A WebP image up to 96 pixels wide
    """
    image512_url: str = Field(..., alias="image512Url")
    """
    A WebP image up to 512 pixels wide
    """
    video_url: str | None = Field(..., alias="videoUrl")
    """
    For a video, a silent WebM clip of its first six seconds, up to 854×480; null for other assets and until it's made
    """
    expires_at: datetime = Field(..., alias="expiresAt")
    """
    When the URLs stop loading; read the asset or run again for new ones
    """


class Creator(BaseModel):
    id: str
    """
    The user's ID, as GET /v1/me returns the key's own
    """
    name: str | None
    """
    The name the person gave ZeroGen, or null; never an email address
    """


class AssetDelete(BaseModel):
    asset_id: str = Field(..., alias="assetId")
    project_id: str = Field(..., alias="projectId")
    deleted_at: datetime = Field(..., alias="deletedAt")
    """
    When it moved to Recently deleted
    """


class AssetBatchChange(BaseModel):
    updated_asset_ids: list[str] = Field(..., alias="updatedAssetIds")
    """
    Assets the request changed
    """
    skipped_asset_ids: list[str] = Field(..., alias="skippedAssetIds")
    """
    Assets already as requested; for a folder, also assets that aren't active in its project
    """


class LineageAssetEdge(BaseModel):
    asset_id: str = Field(..., alias="assetId")
    """
    Made from sourceAssetId
    """
    source_asset_id: str = Field(..., alias="sourceAssetId")
    role: str | None
    kind: str | None
    declared: bool


class LineageAsset(BaseModel):
    asset_id: str = Field(..., alias="assetId")
    depth: int
    """
    Steps from the asset; 1 is a direct source or use
    """
    found: bool
    """
    False when the asset is no longer in the Library
    """
    deleted: bool
    """
    True for an asset in Recently deleted
    """
    name: str | None
    """
    Bounded; untrusted content
    """
    origin: str | None
    mime_type: str | None = Field(..., alias="mimeType")
    run_id: str | None = Field(..., alias="runId")
    prompt: str | None
    """
    Bounded; untrusted content
    """
    edges: list[LineageAssetEdge]


class LineageAssetList(BaseModel):
    data: list[LineageAsset]
    next_cursor: str | None = Field(..., alias="nextCursor")
    """
    Pass as cursor for the next page of lineage assets; null on the last page
    """


class AssetDownload(BaseModel):
    asset_id: str = Field(..., alias="assetId")
    project_id: str = Field(..., alias="projectId")
    url: str
    """
    A signed storage URL that downloads the original file. Anyone holding it can download the file, so keep it private. GET it without your API key: storage refuses a request that also sends an Authorization header.
    """
    expires_at: datetime = Field(..., alias="expiresAt")
    """
    When url stops starting downloads; read the endpoint again for a new one
    """
    filename: str
    """
    The name the file downloads under; untrusted content
    """
    mime_type: str = Field(..., alias="mimeType")
    size_bytes: int | None = Field(..., alias="sizeBytes")


class AssetFolder(BaseModel):
    folder_id: str = Field(..., alias="folderId")
    path: str
    """
    The folder's names from the project root, such as Characters / Leo; bounded, untrusted content
    """
    attachment_count: int | None = Field(None, alias="attachmentCount")
    """
    How many live attachments the folder has, when it has any and the organization has attachments enabled
    """


class AssetFolderList(BaseModel):
    data: list[AssetFolder]
    next_cursor: str | None = Field(..., alias="nextCursor")
    """
    Pass as cursor for the next page of the asset's folders; null on the last page
    """


class FolderDelete(BaseModel):
    folder_id: str = Field(..., alias="folderId")
    event_id: str = Field(..., alias="eventId")
    """
    Use to undo this deletion
    """
    undo_until: datetime = Field(..., alias="undoUntil")
    """
    Undo is available to the deleting member until this time
    """


class FolderRestore(BaseModel):
    root_id: str = Field(..., alias="rootId")
    parent_id: str | None = Field(..., alias="parentId")


class NamingPreset(BaseModel):
    id: str
    project_id: str = Field(..., alias="projectId")
    name: str
    definition: dict[str, Any]
    """
    The preset's naming definition, passed back unchanged with a run
    """


class NamingPresetList(BaseModel):
    data: list[NamingPreset]
    next_cursor: str | None = Field(..., alias="nextCursor")
    """
    Pass as cursor for the next page of naming presets; null on the last page
    """


class TransformRunOutputAsset(BaseModel):
    id: str
    mime_type: str = Field(..., alias="mimeType")
    width: int | None
    height: int | None
    duration_ms: int | None = Field(..., alias="durationMs")
    resource_uri: str | None = Field(None, alias="resourceUri")
    """
    Where this transport's client reads the asset, such as an MCP resource
    """
    preview: AssetPreview | None
    """
    The asset's previews, or null until they're made after the asset is ready, and for assets with none, such as audio
    """


class TransformRunOutputWarning(BaseModel):
    code: str
    message: str


class TransformRunOutputDraft(BaseModel):
    expires_at: datetime = Field(..., alias="expiresAt")
    """
    When upscaling this output closes
    """
    upscalable: bool
    """
    A final can be requested now: unexpired, with no final in progress
    """
    upscale: Literal["upscaling", "upscaled"] | str | None
    """
    The newest final's state, or null when none was requested
    """
    final_resolution: str | None = Field(None, alias="finalResolution")
    """
    That final's resolution, one the model's draft control lists
    """
    final_asset_id: str | None = Field(None, alias="finalAssetId")
    """
    The newest finished final's asset
    """


class TransformRunBillingHold(BaseModel):
    state: Literal["running", "ended", "needs_attention"] | str
    """
    running: the run has not ended; ended: it ended and the hold is still pending; needs_attention: it has stayed pending 30 minutes after ending, or 24 hours after admission with no end recorded (endedAt then stays null), so ZeroGen is looking into it
    """
    ended_at: datetime | None = Field(..., alias="endedAt")
    """
    When the run ended; null while it runs or when no end was recorded
    """


class TransformRunBilling(BaseModel):
    mode: Literal["platform", "byok", "test"] | str
    state: Literal["held", "charged", "released"] | str | None
    """
    held: an amount is reserved and nothing is charged yet; charged: chargedMicroUsd is the final charge; released: the hold ended with no charge; null: billing never admitted the run, so nothing was held or charged
    """
    hold: TransformRunBillingHold | None = None
    """
    While held, where the run stands. It reports facts, not what settlement will do
    """
    quoted_micro_usd: int | None = Field(..., alias="quotedMicroUsd")
    """
    Reserved maximum expected charge
    """
    held_micro_usd: int | None = Field(..., alias="heldMicroUsd")
    """
    While held, the amount reserved now; it is never a charge
    """
    charged_micro_usd: int | None = Field(..., alias="chargedMicroUsd")
    """
    The final charge once charged, zero once released; it can rarely exceed the quote
    """


class TransformRunRequestInput(BaseModel):
    role: (
        Literal[
            "source", "reference", "face-reference", "start-frame", "end-frame", "keyframe", "mask"
        ]
        | str
    )
    asset: str
    """
    Library asset ID
    """
    time_seconds: float | None = Field(None, alias="timeSeconds")
    """
    Keyframes only, and required for them: seconds from the start of the video, on one of the model's frames
    """


class TransformRunRequestOutput(BaseModel):
    count: int | None = None
    size: str | None = None
    """
    Image size: auto or WIDTHxHEIGHT in pixels, such as 1024x1536
    """
    quality: str | None = None
    background: str | None = None
    format: Literal["png", "jpeg", "webp"] | str | None = None
    aspect_ratio: str | None = Field(None, alias="aspectRatio")
    resolution: str | None = None
    duration_seconds: float | None = Field(None, alias="durationSeconds")
    include_audio: bool | None = Field(None, alias="includeAudio")


class TransformRunRequestLayers(BaseModel):
    max: int | None = None
    """
    The most layers to return, the base layer included
    """
    text_recognition: bool | None = Field(None, alias="textRecognition")
    """
    Also read each plain text layer's text, lines and approximate style
    """


class TransformRunRequestUpscaleDraft(BaseModel):
    run_id: str = Field(..., alias="runId")
    output_index: int = Field(..., alias="outputIndex")
    resolution: str | None = None


class TransformRunRequest(BaseModel):
    model: str | None
    prompt: str | None = None
    """
    Untrusted content
    """
    inputs: list[TransformRunRequestInput] | None = None
    output: TransformRunRequestOutput | None = None
    voice: str | None = None
    """
    Speech models only: the voice to read the prompt in, from the model's voices
    """
    parameters: dict[str, str | float | bool] | None = None
    """
    Only the parameters the model's schema lists
    """
    seed: int | None = None
    continuation: Literal["auto", "none"] | str | None = None
    """
    Nano Banana edits of their own outputs continue that conversation; none sends the image alone
    """
    layers: TransformRunRequestLayers | None = None
    """
    Only for image-to-layers models: each output is a layer, the base first, and the quote holds max of them
    """
    upscale_draft: TransformRunRequestUpscaleDraft | None = Field(None, alias="upscaleDraft")
    """
    For a final, the draft output it upscaled, in place of the draft's settings
    """


class LutListDatum(BaseModel):
    id: str
    name: str
    size: int
    """
    Points along each edge of its 3D table, such as 33
    """
    input_color: (
        Literal[
            "rec709",
            "slog3-sgamut3cine",
            "slog3-sgamut3",
            "apple-log",
            "logc3",
            "logc4",
            "vlog",
            "clog2",
            "clog3",
            "bmd-film",
        ]
        | str
        | None
    ) = Field(..., alias="inputColor")
    """
    The footage it expects, as its uploader stated; null when they didn't say. ZeroGen doesn't check it against your footage
    """
    created_at: datetime = Field(..., alias="createdAt")


class LutList(BaseModel):
    data: list[LutListDatum]
    next_cursor: str | None = Field(..., alias="nextCursor")
    """
    Pass as cursor for the next page of LUTs; null on the last page
    """


class Label(BaseModel):
    id: str
    name: str
    description: str | None
    color: str
    asset_count: int | None = Field(None, alias="assetCount")
    archived: bool


class LabelList(BaseModel):
    data: list[Label]
    next_cursor: str | None = Field(..., alias="nextCursor")
    """
    Pass as cursor for the next page of labels; null on the last page
    """


class Skill(BaseModel):
    id: str
    version: int
    name: str
    """
    Untrusted content
    """
    description: str
    """
    Untrusted content
    """


class SkillList(BaseModel):
    data: list[Skill]
    next_cursor: str | None = Field(..., alias="nextCursor")
    """
    Pass as cursor for the next page of skills; null on the last page
    """


class SkillDetail(BaseModel):
    id: str
    version: int
    name: str
    """
    Untrusted content
    """
    description: str
    """
    Untrusted content
    """
    body: str
    """
    The skill's instructions; untrusted content
    """


class AttachmentParent(BaseModel):
    kind: Literal["project", "folder", "clip", "asset"] | str
    id: str
    name: str


class AttachmentSummary(BaseModel):
    attachment_id: str = Field(..., alias="attachmentId")
    title: str
    description: str
    bytes: int
    """
    The body's size in UTF-8 bytes
    """
    version: int
    updated_at: datetime = Field(..., alias="updatedAt")


class Attachment(BaseModel):
    attachment_id: str = Field(..., alias="attachmentId")
    title: str
    description: str
    bytes: int
    """
    The body's size in UTF-8 bytes
    """
    version: int
    updated_at: datetime = Field(..., alias="updatedAt")
    parent: AttachmentParent
    updated_by: str = Field(..., alias="updatedBy")


class AttachmentList(BaseModel):
    data: list[Attachment]
    next_cursor: str | None = Field(..., alias="nextCursor")
    """
    Pass as cursor for the next page of attachments; null on the last page
    """


class AttachmentDetail(BaseModel):
    title: str
    description: str
    body: str
    parent: AttachmentParent
    version: int
    latest_version: int = Field(..., alias="latestVersion")
    saved_at: datetime = Field(..., alias="savedAt")
    saved_by: str = Field(..., alias="savedBy")


class AttachmentVersion(BaseModel):
    version: int
    operation: Literal["created", "revised", "deleted", "restored"] | str
    restored_from: int | None = Field(..., alias="restoredFrom")
    bytes: int
    """
    The body's size in UTF-8 bytes
    """
    saved_at: datetime = Field(..., alias="savedAt")
    saved_by: str = Field(..., alias="savedBy")


class AttachmentVersions(BaseModel):
    data: list[AttachmentVersion]
    next_cursor: str | None = Field(..., alias="nextCursor")
    """
    Pass as cursor for the next page of attachment versions; null on the last page
    """


class AttachmentCreate(BaseModel):
    project_id: str = Field(..., alias="projectId")
    version: int
    attachment_id: str = Field(..., alias="attachmentId")
    outcome: Literal["created", "unchanged"] | str


class AttachmentRevise(BaseModel):
    project_id: str = Field(..., alias="projectId")
    version: int
    outcome: Literal["revised", "unchanged"] | str


class AttachmentDelete(BaseModel):
    project_id: str = Field(..., alias="projectId")
    version: int
    outcome: Literal["deleted", "unchanged"] | str


class AttachmentRestore(BaseModel):
    project_id: str = Field(..., alias="projectId")
    version: int
    restored_from: int = Field(..., alias="restoredFrom")
    outcome: Literal["restored", "unchanged"] | str


class ErrorDetails(BaseModel):
    model_config = ConfigDict(
        extra="allow",
    )
    __annotations__ = {
        "__pydantic_extra__": Dict[str, Any],
    }
    reason: str | None = None
    """
    The cause. Stable for rate_limited (request_limit, running_cap, platform_capacity, url_import_limit) and permission_denied (scope_required, role_required, not_creator, feature_not_enabled, early_access, test_key_sandbox, browser_request); for a run or output error, for diagnosis only
    """


class Error(BaseModel):
    code: str
    message: str
    param: str | None = None
    retryable: bool
    details: ErrorDetails | None = None
    """
    More facts about the error; each code says which it carries
    """


class ErrorResponse(BaseModel):
    error: Error


class RunOutputAsset(BaseModel):
    id: str
    mime_type: str = Field(..., alias="mimeType")
    width: int | None
    height: int | None
    duration_ms: int | None = Field(..., alias="durationMs")
    resource_uri: str | None = Field(None, alias="resourceUri")
    """
    Where this transport's client reads the asset, such as an MCP resource
    """
    preview: AssetPreview | None
    """
    The asset's previews, or null until they're made after the asset is ready, and for assets with none, such as audio
    """


class RunOutput(BaseModel):
    index: int
    status: Literal["queued", "running", "succeeded", "failed", "cancelled"] | str
    asset: RunOutputAsset | None
    error: Error | None
    warnings: list[RunOutputWarning] | None = None
    """
    What the provider ignored, such as an unused reference
    """
    draft: RunOutputDraft | None = None
    """
    A 480p Draft output; upscaling it makes a final with the same seed, at a resolution the model's draft control lists
    """


class Run(BaseModel):
    id: str
    project_id: str = Field(..., alias="projectId")
    """
    The project that holds the outputs
    """
    kind: Literal["generation", "transform", "upload"] | str
    model: str | None
    model_version: str | None = Field(..., alias="modelVersion")
    status: Literal["queued", "running", "succeeded", "partial", "failed", "cancelled"] | str
    """
    queued and running mean the run hasn't ended. On every other status, check each output: a cancelled or failed run can still hold succeeded outputs, which are kept and charged
    """
    outputs: list[RunOutput]
    error: Error | None
    billing: RunBilling
    created_by: Creator | None = Field(..., alias="createdBy")
    """
    Who made it; null when ZeroGen recorded no one
    """
    created_via: Literal["web", "agent", "mcp", "api"] | str | None = Field(..., alias="createdVia")
    """
    Where it was made: web (the ZeroGen app), agent (ZeroGen's Agent), mcp (an MCP client) or api (an API key); null with createdBy
    """
    created_at: datetime = Field(..., alias="createdAt")
    started_at: datetime | None = Field(..., alias="startedAt")
    finished_at: datetime | None = Field(..., alias="finishedAt")
    """
    When ZeroGen recorded the run's end; prefer endedAt to tell whether it has ended
    """
    ended_at: datetime | None = Field(..., alias="endedAt")
    """
    When the run ended: set exactly when it has, whatever its status, and null while it runs. Stop waiting once it's set
    """
    request: RunRequest | None
    web_url: str | None = Field(..., alias="webUrl")
    """
    Opens Generate's review of the run's first ready output in ZeroGen, on your organization's host, after sign-in. null until an output is ready, and for test keys. It can change until the run ends
    """


class RunList(BaseModel):
    data: list[Run]
    next_cursor: str | None = Field(..., alias="nextCursor")
    """
    Pass as cursor for the next page of runs; null on the last page
    """


class AssetDeclarationAsset(BaseModel):
    id: str
    project_id: str = Field(..., alias="projectId")
    name: str
    """
    The asset's name in the Library; untrusted content
    """
    type: Literal["image", "video", "audio", "model3d"] | str
    origin: Literal["generated", "upload", "derived"] | str
    """
    upload: added by a person or a URL import; generated: an output of a run; derived: made by a platform step, such as an extracted frame
    """
    mime_type: str = Field(..., alias="mimeType")
    size_bytes: int | None = Field(..., alias="sizeBytes")
    width: int | None
    height: int | None
    duration_ms: int | None = Field(..., alias="durationMs")
    favorite: bool
    """
    The organization's shared favorite
    """
    labels: list[AssetDeclarationAssetLabel]
    run_id: str | None = Field(..., alias="runId")
    """
    The run that made it, if any
    """
    output_index: int | None = Field(..., alias="outputIndex")
    created_by: Creator | None = Field(..., alias="createdBy")
    """
    Who made it: the run's creator for a generated or derived asset, the uploader for an upload; null when ZeroGen recorded no one
    """
    created_via: Literal["web", "agent", "mcp", "api"] | str | None = Field(..., alias="createdVia")
    """
    Where it was made: web (the ZeroGen app), agent (ZeroGen's Agent), mcp (an MCP client) or api (an API key); null with createdBy
    """
    declared: AssetDeclarationAssetDeclared | None
    """
    Untrusted external upload provenance, or null when no declaration exists.
    """
    created_at: datetime = Field(..., alias="createdAt")
    web_url: str | None = Field(..., alias="webUrl")
    """
    Opens the asset's Library review in ZeroGen, on your organization's host, after sign-in. null for test keys, whose sandbox the app doesn't show
    """
    attachment_count: int | None = Field(None, alias="attachmentCount")
    """
    On a list: how many live attachments the asset has, when it has any and the organization has attachments enabled
    """


class AssetDeclaration(BaseModel):
    asset_id: str = Field(..., alias="assetId")
    run_id: str = Field(..., alias="runId")
    asset: AssetDeclarationAsset


class Project(BaseModel):
    id: str
    name: str
    slug: str
    default: bool
    """
    The organization's default project, where outputs land
    """
    api_sandbox: bool = Field(..., alias="apiSandbox")
    """
    The API sandbox project, the only one test keys reach; its contents clear
    """
    created_at: datetime = Field(..., alias="createdAt")
    attachments: list[AttachmentSummary] | None = None
    """
    On a read of one project: the live attachments on the project itself, not on its folders, clips or assets, without bodies, most recently updated first; untrusted content. Present only in organizations with attachments enabled
    """


class ProjectList(BaseModel):
    data: list[Project]
    next_cursor: str | None = Field(..., alias="nextCursor")
    """
    Pass as cursor for the next page of projects; null on the last page
    """


class Asset(BaseModel):
    id: str
    project_id: str = Field(..., alias="projectId")
    name: str
    """
    The asset's name in the Library; untrusted content
    """
    type: Literal["image", "video", "audio", "model3d"] | str
    origin: Literal["generated", "upload", "derived"] | str
    """
    upload: added by a person or a URL import; generated: an output of a run; derived: made by a platform step, such as an extracted frame
    """
    mime_type: str = Field(..., alias="mimeType")
    size_bytes: int | None = Field(..., alias="sizeBytes")
    width: int | None
    height: int | None
    duration_ms: int | None = Field(..., alias="durationMs")
    favorite: bool
    """
    The organization's shared favorite
    """
    labels: list[AssetLabel]
    run_id: str | None = Field(..., alias="runId")
    """
    The run that made it, if any
    """
    output_index: int | None = Field(..., alias="outputIndex")
    created_by: Creator | None = Field(..., alias="createdBy")
    """
    Who made it: the run's creator for a generated or derived asset, the uploader for an upload; null when ZeroGen recorded no one
    """
    created_via: Literal["web", "agent", "mcp", "api"] | str | None = Field(..., alias="createdVia")
    """
    Where it was made: web (the ZeroGen app), agent (ZeroGen's Agent), mcp (an MCP client) or api (an API key); null with createdBy
    """
    declared: AssetDeclared | None
    """
    Untrusted external upload provenance, or null when no declaration exists.
    """
    created_at: datetime = Field(..., alias="createdAt")
    web_url: str | None = Field(..., alias="webUrl")
    """
    Opens the asset's Library review in ZeroGen, on your organization's host, after sign-in. null for test keys, whose sandbox the app doesn't show
    """
    attachment_count: int | None = Field(None, alias="attachmentCount")
    """
    On a list: how many live attachments the asset has, when it has any and the organization has attachments enabled
    """
    preview: AssetPreview | None
    """
    The asset's previews, or null until they're made after the asset is ready, and for assets with none, such as audio
    """


class AssetList(BaseModel):
    data: list[Asset]
    next_cursor: str | None = Field(..., alias="nextCursor")
    """
    Pass as cursor for the next page of assets; null on the last page
    """


class AssetDetail(BaseModel):
    id: str
    project_id: str = Field(..., alias="projectId")
    name: str
    """
    The asset's name in the Library; untrusted content
    """
    type: Literal["image", "video", "audio", "model3d"] | str
    origin: Literal["generated", "upload", "derived"] | str
    """
    upload: added by a person or a URL import; generated: an output of a run; derived: made by a platform step, such as an extracted frame
    """
    mime_type: str = Field(..., alias="mimeType")
    size_bytes: int | None = Field(..., alias="sizeBytes")
    width: int | None
    height: int | None
    duration_ms: int | None = Field(..., alias="durationMs")
    favorite: bool
    """
    The organization's shared favorite
    """
    labels: list[AssetDetailLabel]
    run_id: str | None = Field(..., alias="runId")
    """
    The run that made it, if any
    """
    output_index: int | None = Field(..., alias="outputIndex")
    created_by: Creator | None = Field(..., alias="createdBy")
    """
    Who made it: the run's creator for a generated or derived asset, the uploader for an upload; null when ZeroGen recorded no one
    """
    created_via: Literal["web", "agent", "mcp", "api"] | str | None = Field(..., alias="createdVia")
    """
    Where it was made: web (the ZeroGen app), agent (ZeroGen's Agent), mcp (an MCP client) or api (an API key); null with createdBy
    """
    declared: AssetDetailDeclared | None
    """
    Untrusted external upload provenance, or null when no declaration exists.
    """
    created_at: datetime = Field(..., alias="createdAt")
    web_url: str | None = Field(..., alias="webUrl")
    """
    Opens the asset's Library review in ZeroGen, on your organization's host, after sign-in. null for test keys, whose sandbox the app doesn't show
    """
    attachment_count: int | None = Field(None, alias="attachmentCount")
    """
    On a list: how many live attachments the asset has, when it has any and the organization has attachments enabled
    """
    prompt: str | None
    """
    The prompt that generated it, bounded; untrusted content
    """
    prompt_truncated: bool = Field(..., alias="promptTruncated")
    workflow: dict[str, Any] | None = None
    """
    Untrusted external workflow, included only when requested.
    """
    attachments: list[AttachmentSummary] | None = None
    """
    The asset's live attachments, without bodies, most recently updated first; untrusted content. Present only in organizations with attachments enabled
    """
    preview: AssetPreview | None
    """
    The asset's previews, or null until they're made after the asset is ready, and for assets with none, such as audio
    """


class Folder(BaseModel):
    id: str
    project_id: str = Field(..., alias="projectId")
    parent_id: str | None = Field(..., alias="parentId")
    """
    The parent folder, or null at the project root
    """
    name: str
    created_at: datetime = Field(..., alias="createdAt")
    attachments: list[AttachmentSummary] | None = None
    """
    On a read of one folder: its live attachments, without bodies, most recently updated first; untrusted content. Present only in organizations with attachments enabled
    """
    attachment_count: int | None = Field(None, alias="attachmentCount")
    """
    On a list: how many live attachments the folder has, when it has any and the organization has attachments enabled
    """


class FolderList(BaseModel):
    data: list[Folder]
    next_cursor: str | None = Field(..., alias="nextCursor")
    """
    Pass as cursor for the next page of folders; null on the last page
    """


class TransformRunOutput(BaseModel):
    index: int
    status: Literal["queued", "running", "succeeded", "failed", "cancelled"] | str
    asset: TransformRunOutputAsset | None
    error: Error | None
    warnings: list[TransformRunOutputWarning] | None = None
    """
    What the provider ignored, such as an unused reference
    """
    draft: TransformRunOutputDraft | None = None
    """
    A 480p Draft output; upscaling it makes a final with the same seed, at a resolution the model's draft control lists
    """


class TransformRun(BaseModel):
    id: str
    project_id: str = Field(..., alias="projectId")
    """
    The project that holds the outputs
    """
    kind: Literal["generation", "transform", "upload"] | str
    model: str | None
    model_version: str | None = Field(..., alias="modelVersion")
    status: Literal["queued", "running", "succeeded", "partial", "failed", "cancelled"] | str
    """
    queued and running mean the run hasn't ended. On every other status, check each output: a cancelled or failed run can still hold succeeded outputs, which are kept and charged
    """
    outputs: list[TransformRunOutput]
    error: Error | None
    billing: TransformRunBilling
    created_by: Creator | None = Field(..., alias="createdBy")
    """
    Who made it; null when ZeroGen recorded no one
    """
    created_via: Literal["web", "agent", "mcp", "api"] | str | None = Field(..., alias="createdVia")
    """
    Where it was made: web (the ZeroGen app), agent (ZeroGen's Agent), mcp (an MCP client) or api (an API key); null with createdBy
    """
    created_at: datetime = Field(..., alias="createdAt")
    started_at: datetime | None = Field(..., alias="startedAt")
    finished_at: datetime | None = Field(..., alias="finishedAt")
    """
    When ZeroGen recorded the run's end; prefer endedAt to tell whether it has ended
    """
    ended_at: datetime | None = Field(..., alias="endedAt")
    """
    When the run ended: set exactly when it has, whatever its status, and null while it runs. Stop waiting once it's set
    """
    request: TransformRunRequest | None
    web_url: str | None = Field(..., alias="webUrl")
    """
    Opens Generate's review of the run's first ready output in ZeroGen, on your organization's host, after sign-in. null until an output is ready, and for test keys. It can change until the run ends
    """
    reused: bool
    """
    True when this is your earlier run of the same recipe on this asset for the same destination, finished or in progress, so no new work started
    """
