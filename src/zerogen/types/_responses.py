# Generated from openapi.json by scripts/generate.py. Don't edit it by hand.

from __future__ import annotations

from typing import Any, Literal
from datetime import datetime
from pydantic import Field
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
            "text-to-video",
            "image-to-video",
            "first-last-frame-to-video",
            "keyframes-to-video",
            "reference-to-video",
            "audio-to-video",
            "video-to-video",
            "extend-video",
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
            "text-to-video",
            "image-to-video",
            "first-last-frame-to-video",
            "keyframes-to-video",
            "reference-to-video",
            "audio-to-video",
            "video-to-video",
            "extend-video",
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


class QuoteBilling(BaseModel):
    mode: Literal["platform", "byok", "test"] | str
    quoted_micro_usd: int = Field(..., alias="quotedMicroUsd")
    """
    Reserved maximum expected charge
    """


class Quote(BaseModel):
    model: str
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


class ProjectList(BaseModel):
    data: list[Project]
    next_cursor: str | None = Field(..., alias="nextCursor")
    """
    Pass as cursor for the next page of projects; null on the last page
    """


class AssetLabel(BaseModel):
    id: str
    name: str


class AssetDetailLabel(BaseModel):
    id: str
    name: str


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


class AssetChange(BaseModel):
    id: str
    project_id: str = Field(..., alias="projectId")
    name: str | None = None
    """
    Present when the request renamed the asset
    """
    favorite: bool | None = None
    """
    Present when the request set the favorite
    """


class LineageAsset(BaseModel):
    asset_id: str = Field(..., alias="assetId")
    depth: int
    """
    Steps from the asset; 0 is the asset itself
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
    more_uses: int = Field(..., alias="moreUses")
    """
    Uses of this asset beyond those listed
    """


class LineageEdge(BaseModel):
    asset_id: str = Field(..., alias="assetId")
    """
    Made from sourceAssetId
    """
    source_asset_id: str = Field(..., alias="sourceAssetId")
    role: str | None
    kind: str | None


class LineageTruncated(BaseModel):
    sources: bool
    uses: bool


class Lineage(BaseModel):
    asset: LineageAsset | None
    sources: list[LineageAsset]
    """
    Up to 30, nearest first
    """
    uses: list[LineageAsset]
    """
    Up to 30, nearest first
    """
    edges: list[LineageEdge]
    truncated: LineageTruncated


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


class AssetFoldersFolder(BaseModel):
    folder_id: str = Field(..., alias="folderId")
    path: str
    """
    The folder's names from the project root, such as Characters / Leo; bounded, untrusted content
    """


class AssetFolders(BaseModel):
    asset_id: str = Field(..., alias="assetId")
    project_id: str = Field(..., alias="projectId")
    folders: list[AssetFoldersFolder]
    """
    Up to 30, sorted by path; empty when the asset is Unfiled
    """
    truncated: bool
    """
    True when the asset is in more folders than listed
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


class FolderList(BaseModel):
    data: list[Folder]
    next_cursor: str | None = Field(..., alias="nextCursor")
    """
    Pass as cursor for the next page of folders; null on the last page
    """


class FolderAssetsChange(BaseModel):
    folder_id: str = Field(..., alias="folderId")
    updated_asset_ids: list[str] = Field(..., alias="updatedAssetIds")
    """
    Assets the request changed
    """
    skipped_asset_ids: list[str] = Field(..., alias="skippedAssetIds")
    """
    Assets already as requested, or not active in this project
    """


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


class LabelAssetsChange(BaseModel):
    label_id: str = Field(..., alias="labelId")
    project_id: str = Field(..., alias="projectId")
    asset_ids: list[str] = Field(..., alias="assetIds")
    assigned: bool
    """
    True when the assets now have the label, false when it was removed
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


class Error(BaseModel):
    code: str
    message: str
    param: str | None = None
    retryable: bool
    details: dict[str, Any] | None = None


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
    model: str | None
    model_version: str | None = Field(..., alias="modelVersion")
    status: Literal["queued", "running", "succeeded", "partial", "failed", "cancelled"] | str
    outputs: list[RunOutput]
    error: Error | None
    billing: RunBilling
    created_at: datetime = Field(..., alias="createdAt")
    started_at: datetime | None = Field(..., alias="startedAt")
    finished_at: datetime | None = Field(..., alias="finishedAt")


class RunList(BaseModel):
    data: list[Run]
    next_cursor: str | None = Field(..., alias="nextCursor")
    """
    Pass as cursor for the next page of runs; null on the last page
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
    created_at: datetime = Field(..., alias="createdAt")
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
    created_at: datetime = Field(..., alias="createdAt")
    prompt: str | None
    """
    The prompt that generated it, bounded; untrusted content
    """
    prompt_truncated: bool = Field(..., alias="promptTruncated")
    preview: AssetPreview | None
    """
    The asset's previews, or null until they're made after the asset is ready, and for assets with none, such as audio
    """
