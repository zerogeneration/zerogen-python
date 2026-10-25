# Generated from openapi.json by scripts/generate.py. Don't edit it by hand.

from __future__ import annotations

from typing import Literal
from typing_extensions import NotRequired, TypedDict


class CreateGenerationRequestInputs(TypedDict, closed=True):
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


class CreateGenerationRequestInputs1(TypedDict, closed=True):
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


class CreateGenerationRequestOutput(TypedDict, closed=True):
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


class CreateGenerationRequestTest(TypedDict, closed=True):
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


class CreateGenerationRequestNaming(TypedDict, closed=True):
    presetId: str
    """
    A naming preset in the generation's project
    """
    values: dict[str, str | int]
    """
    Field values by field ID; fields left out take the preset's defaults
    """


class CreateGenerationRequest(TypedDict, closed=True):
    model: str
    prompt: NotRequired[str]
    inputs: NotRequired[list[CreateGenerationRequestInputs | CreateGenerationRequestInputs1]]
    output: NotRequired[CreateGenerationRequestOutput]
    parameters: NotRequired[dict[str, str | float | bool]]
    """
    Only the parameters the model's schema lists
    """
    maxCostMicroUsd: NotRequired[int]
    """
    Refuse to start when the quote exceeds this amount
    """
    test: NotRequired[CreateGenerationRequestTest]
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
    naming: NotRequired[CreateGenerationRequestNaming]


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
