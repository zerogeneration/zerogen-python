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
    Reserved for generations that have not settled; a hold is not a charge
    """
    available_micro_usd: int = Field(..., alias="availableMicroUsd")
    """
    What a new generation's quote must fit within; it can be negative
    """
    unlimited: bool
    """
    The funds check is bypassed; usage is still charged
    """
    limits: BalanceLimits


class Model(BaseModel):
    id: str
    name: str
    capability: Literal["image", "video"] | str
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
            "clean-plate",
            "render-to-real",
            "hdr",
            "outpaint",
            "reference-video-to-video",
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
    capability: Literal["image", "video"] | str
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
            "clean-plate",
            "render-to-real",
            "hdr",
            "outpaint",
            "reference-video-to-video",
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
    JSON Schema (2020-12) for POST /v1/generations with this model; x-roles lists each input role's accepted media and limits
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


class GenerationOutputAsset(BaseModel):
    id: str
    mime_type: str = Field(..., alias="mimeType")
    width: int | None
    height: int | None
    duration_ms: int | None = Field(..., alias="durationMs")
    resource_uri: str | None = Field(None, alias="resourceUri")
    """
    Where this transport's client reads the asset, such as an MCP resource
    """


class GenerationOutputWarning(BaseModel):
    code: str
    message: str


class GenerationOutputDraft(BaseModel):
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


class GenerationBillingHold(BaseModel):
    state: Literal["running", "ended", "needs_attention"] | str
    """
    running: the generation has not ended; ended: it ended and the hold is still pending; needs_attention: it has stayed pending 30 minutes after ending, or 24 hours after admission with no end recorded (endedAt then stays null), so ZeroGen is looking into it
    """
    ended_at: datetime | None = Field(..., alias="endedAt")
    """
    When the generation ended; null while it runs or when no end was recorded
    """


class GenerationBilling(BaseModel):
    mode: Literal["platform", "byok", "test"] | str
    state: Literal["held", "charged", "released"] | str | None
    """
    held: an amount is reserved and nothing is charged yet; charged: chargedMicroUsd is the final charge; released: the hold ended with no charge; null: billing never admitted the generation, so nothing was held or charged
    """
    hold: GenerationBillingHold | None = None
    """
    While held, where the generation stands. It reports facts, not what settlement will do
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
    Once ready, the Library asset to send as a generation input; an identical file already in the project is reused
    """
    upload: UploadUpload | None
    """
    Where to PUT the file's exact bytes, with these headers, before expiresAt
    """
    folder: UploadFolder | None = None
    """
    Whether the asset was added to the folder named at create
    """


class Error(BaseModel):
    code: str
    message: str
    param: str | None = None
    retryable: bool
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    error: Error


class GenerationOutput(BaseModel):
    index: int
    status: Literal["queued", "running", "succeeded", "failed", "cancelled"] | str
    asset: GenerationOutputAsset | None
    error: Error | None
    warnings: list[GenerationOutputWarning] | None = None
    """
    What the provider ignored, such as an unused reference
    """
    draft: GenerationOutputDraft | None = None
    """
    A 480p Draft output; upscaling it makes a final with the same seed, at a resolution the model's draft control lists
    """


class Generation(BaseModel):
    id: str
    project_id: str = Field(..., alias="projectId")
    """
    The project that holds the outputs
    """
    model: str | None
    model_version: str | None = Field(..., alias="modelVersion")
    status: Literal["queued", "running", "succeeded", "partial", "failed", "cancelled"] | str
    outputs: list[GenerationOutput]
    error: Error | None
    billing: GenerationBilling
    created_at: datetime = Field(..., alias="createdAt")
    started_at: datetime | None = Field(..., alias="startedAt")
    finished_at: datetime | None = Field(..., alias="finishedAt")


class GenerationList(BaseModel):
    data: list[Generation]
    next_cursor: str | None = Field(..., alias="nextCursor")
    """
    Pass as cursor for the next page of generations; null on the last page
    """
