# Generated from openapi.json by scripts/generate.py. Don't edit it by hand.

from __future__ import annotations

from typing import Literal, TypeAlias
from typing_extensions import NotRequired, TypedDict


class CreateRunRequestInputs(TypedDict, closed=True):
    role: Literal[
        "source", "reference", "face-reference", "start-frame", "end-frame", "keyframe", "mask"
    ]
    asset: str
    """
    Library asset ID
    """
    timeSeconds: NotRequired[float]
    """
    Keyframes only, and required for them: seconds from the start of the video, on one of the model's frames
    """


class CreateRunRequestInputs1(TypedDict, closed=True):
    role: Literal[
        "source", "reference", "face-reference", "start-frame", "end-frame", "keyframe", "mask"
    ]
    url: str
    """
    An https URL ZeroGen imports into the library before use
    """
    timeSeconds: NotRequired[float]
    """
    Keyframes only, and required for them: seconds from the start of the video, on one of the model's frames
    """


class CreateRunRequestOutput(TypedDict, closed=True):
    count: NotRequired[int]
    size: NotRequired[str]
    """
    Image size: auto or WIDTHxHEIGHT in pixels, such as 1024x1536
    """
    quality: NotRequired[str]
    background: NotRequired[str]
    format: NotRequired[Literal["png", "jpeg", "webp"]]
    aspectRatio: NotRequired[str]
    resolution: NotRequired[str]
    durationSeconds: NotRequired[float]
    includeAudio: NotRequired[bool]


class CreateRunRequestTest(TypedDict, closed=True):
    outputs: NotRequired[
        list[
            Literal[
                "succeeded",
                "provider_error",
                "provider_timeout",
                "content_moderation",
                "input_rejected",
            ]
        ]
    ]
    """
    Each output's outcome, in order: succeeded, or the error code a live output can end with. Outputs left out succeed
    """
    reject: NotRequired[Literal["insufficient_balance", "rate_limited", "model_unavailable"]]
    """
    Create only: refuse with this live response and start nothing (402 insufficient_balance, 429 rate_limited with Retry-After, 400 model_unavailable)
    """
    delaySeconds: NotRequired[int]
    """
    Seconds before each output ends, to rehearse polling and Prefer: wait
    """


class CreateRunRequestNaming(TypedDict, closed=True):
    presetId: str
    """
    A naming preset in the run's project
    """
    values: dict[str, str | int]
    """
    Field values by field ID; fields left out take the preset's defaults
    """


class CreateRunRequest(TypedDict, closed=True):
    model: str
    prompt: NotRequired[str]
    inputs: NotRequired[list[CreateRunRequestInputs | CreateRunRequestInputs1]]
    output: NotRequired[CreateRunRequestOutput]
    voice: NotRequired[str]
    """
    Speech models only: the voice to read the prompt in, from the model's voices
    """
    parameters: NotRequired[dict[str, str | float | bool]]
    """
    Only the parameters the model's schema lists
    """
    maxCostMicroUsd: NotRequired[int]
    """
    Refuse to start when the quote exceeds this amount
    """
    test: NotRequired[CreateRunRequestTest]
    """
    Test keys only: rehearse each output's outcome; live keys are refused when it is present
    """
    projectId: NotRequired[str]
    """
    The project the outputs land in; the organization's default project when omitted. Test keys use their sandbox.
    """
    folderId: NotRequired[str | None]
    """
    A folder in that project to file the outputs in; null or omitted for Unfiled
    """
    naming: NotRequired[CreateRunRequestNaming]


class CreateUploadRequest(TypedDict, closed=True):
    projectId: NotRequired[str]
    """
    The project to upload into; omit for the organization's default project.
    """
    folderId: NotRequired[str]
    """
    Add the asset to this folder in the project.
    """
    filename: str
    contentType: Literal[
        "audio/aac",
        "audio/aiff",
        "audio/flac",
        "audio/mp4",
        "audio/mpeg",
        "audio/ogg",
        "audio/wav",
        "image/avif",
        "image/bmp",
        "image/gif",
        "image/jpeg",
        "image/png",
        "image/tiff",
        "image/webp",
        "video/mp4",
        "video/quicktime",
        "video/webm",
        "video/x-matroska",
        "video/x-msvideo",
    ]
    sizeBytes: int
    sha256: NotRequired[str]
    """
    Lowercase hex SHA-256 of the file, to reuse an identical file in the project.
    """


class UpdateAssetRequest(TypedDict, closed=True):
    name: NotRequired[str]
    favorite: NotRequired[bool]
    """
    The organization's shared favorite
    """


class CreateFolderRequest(TypedDict, closed=True):
    name: str
    parentId: NotRequired[str | None]
    """
    The parent folder; omit or null for the project root
    """


class UpdateFolderRequest(TypedDict, closed=True):
    name: NotRequired[str]
    parentId: NotRequired[str | None]
    """
    The new parent folder, or null to move it to the project root
    """


FolderAssetsRequestAssetId: TypeAlias = str


class FolderAssetsRequest(TypedDict, closed=True):
    assetIds: list[FolderAssetsRequestAssetId]
    """
    Up to 100 assets
    """


MoveAssetsRequestAssetId: TypeAlias = str


class MoveAssetsRequest(TypedDict, closed=True):
    assetIds: list[MoveAssetsRequestAssetId]
    """
    Up to 100 assets
    """
    fromFolderId: str
    """
    The folder to take the assets out of; their other folders keep them
    """


class CreateLabelRequest(TypedDict, closed=True):
    name: str
    description: NotRequired[str]
    color: NotRequired[
        Literal[
            "#ef4444",
            "#f97316",
            "#f59e0b",
            "#eab308",
            "#84cc16",
            "#22c55e",
            "#14b8a6",
            "#06b6d4",
            "#3b82f6",
            "#6366f1",
            "#8b5cf6",
            "#ec4899",
        ]
    ]
    """
    One of the preset colors: Red #ef4444, Orange #f97316, Amber #f59e0b, Yellow #eab308, Lime #84cc16, Green #22c55e, Teal #14b8a6, Cyan #06b6d4, Blue #3b82f6, Indigo #6366f1, Violet #8b5cf6, Pink #ec4899.
    """


class UpdateLabelRequest(TypedDict, closed=True):
    name: str
    description: str
    color: Literal[
        "#ef4444",
        "#f97316",
        "#f59e0b",
        "#eab308",
        "#84cc16",
        "#22c55e",
        "#14b8a6",
        "#06b6d4",
        "#3b82f6",
        "#6366f1",
        "#8b5cf6",
        "#ec4899",
    ]
    """
    One of the preset colors: Red #ef4444, Orange #f97316, Amber #f59e0b, Yellow #eab308, Lime #84cc16, Green #22c55e, Teal #14b8a6, Cyan #06b6d4, Blue #3b82f6, Indigo #6366f1, Violet #8b5cf6, Pink #ec4899.
    """


LabelAssetsRequestAssetId: TypeAlias = str


class LabelAssetsRequest(TypedDict, closed=True):
    assetIds: list[LabelAssetsRequestAssetId]
    """
    Up to 50 assets
    """
