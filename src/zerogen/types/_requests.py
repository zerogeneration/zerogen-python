# Generated from openapi.json by scripts/generate.py. Don't edit it by hand.

from __future__ import annotations

from typing import Any, Literal, TypeAlias
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


CreateRunRequestLabelId: TypeAlias = str


class CreateRunRequestNaming(TypedDict, closed=True):
    presetId: str
    """
    A naming preset in the run's project
    """
    values: dict[str, str | int]
    """
    Field values by field ID; fields left out take the preset's defaults
    """


class CreateRunRequestUpscaleDraft(TypedDict, closed=True):
    runId: str
    outputIndex: int
    resolution: NotRequired[str]
    """
    The final's resolution: 1080p by default, or another that the model's requestSchema lists
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
    seed: NotRequired[int]
    """
    Only for models whose schema lists seed: the same seed with the same request reproduces a result as closely as the model allows. The model picks one when omitted
    """
    continuation: NotRequired[Literal["auto", "none"]]
    """
    Nano Banana edits of their own outputs continue that conversation; none sends the image alone
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
    The project the outputs land in; the organization's default project when omitted, or the draft's with upscaleDraft. Test keys use their sandbox.
    """
    folderId: NotRequired[str | None]
    """
    A folder in that project to file the outputs in; null or omitted for Unfiled
    """
    labelIds: NotRequired[list[CreateRunRequestLabelId]]
    """
    Active organization labels to add to every output as it lands
    """
    naming: NotRequired[CreateRunRequestNaming]
    upscaleDraft: NotRequired[CreateRunRequestUpscaleDraft]
    """
    Upscale one output of a Seedance 2.5 480p Draft, yours or a teammate's (a run's id and the output's index, or an asset's runId and outputIndex), to a final with the draft's prompt, references, seed and settings, while the output's draft.upscalable is true. Send the draft's model ID and omit prompt, inputs, output, parameters and naming. The final is a new run, quoted and billed like any other.
    """


class CreateUploadRequestSource(TypedDict, closed=True):
    asset: str
    """
    An existing readable Library asset; this claim is not verified.
    """
    role: NotRequired[
        Literal[
            "source",
            "initial-frame",
            "end-frame",
            "keyframe",
            "reference",
            "face-reference",
            "identity",
            "driver",
            "mask",
        ]
    ]


class CreateUploadRequestToolIntegration(TypedDict, closed=True):
    name: str
    version: NotRequired[str]


CreateUploadRequestToolModel: TypeAlias = str


class CreateUploadRequestTool(TypedDict, closed=True):
    name: str
    version: NotRequired[str]
    integration: NotRequired[CreateUploadRequestToolIntegration]
    models: NotRequired[list[CreateUploadRequestToolModel]]


class CreateUploadRequestExternalRef(TypedDict, closed=True):
    system: str
    id: str


class CreateUploadRequestNamingDefinitionField(TypedDict, closed=True):
    id: str
    kind: Literal["shot", "take", "artist", "date", "version", "text", "folder"]
    label: str
    prefix: str
    padding: int
    step: int
    sequence: Literal["number", "letters"]
    artistFormat: Literal["initials", "compact", "hyphen", "underscore", "custom"]
    artistNameStyle: NotRequired[Literal["full", "initials"]]
    artistCase: NotRequired[Literal["preserve", "lower", "upper", "title"]]
    artistSeparator: NotRequired[str]
    dateFormat: str
    defaultValue: str
    folderRemoveSpaces: NotRequired[bool]


class CreateUploadRequestNamingDefinition(TypedDict, closed=True):
    delimiter: str
    fields: list[CreateUploadRequestNamingDefinitionField]


class CreateUploadRequestNaming(TypedDict, closed=True):
    presetId: str | None
    definition: CreateUploadRequestNamingDefinition
    values: dict[str, str | int]
    version: NotRequired[int]


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
    sources: NotRequired[list[CreateUploadRequestSource]]
    """
    Untrusted claims about the readable Library sources used outside ZeroGen.
    """
    tool: NotRequired[CreateUploadRequestTool]
    workflow: NotRequired[dict[str, str | float | bool | list[Any] | dict[str, Any] | None]]
    """
    Untrusted JSON workflow, limited to 262144 serialized UTF-8 bytes.
    """
    prompt: NotRequired[str]
    externalRef: NotRequired[CreateUploadRequestExternalRef]
    occurredAt: NotRequired[str]
    naming: NotRequired[CreateUploadRequestNaming]
    """
    An untrusted external naming claim; it is not verification.
    """


class DeclareUploadRequestSource(TypedDict, closed=True):
    asset: str
    """
    An existing readable Library asset; this claim is not verified.
    """
    role: NotRequired[
        Literal[
            "source",
            "initial-frame",
            "end-frame",
            "keyframe",
            "reference",
            "face-reference",
            "identity",
            "driver",
            "mask",
        ]
    ]


class DeclareUploadRequestToolIntegration(TypedDict, closed=True):
    name: str
    version: NotRequired[str]


DeclareUploadRequestToolModel: TypeAlias = str


class DeclareUploadRequestTool(TypedDict, closed=True):
    name: str
    version: NotRequired[str]
    integration: NotRequired[DeclareUploadRequestToolIntegration]
    models: NotRequired[list[DeclareUploadRequestToolModel]]


class DeclareUploadRequestExternalRef(TypedDict, closed=True):
    system: str
    id: str


class DeclareUploadRequest(TypedDict, closed=True):
    sources: NotRequired[list[DeclareUploadRequestSource]]
    """
    Untrusted claims about the readable Library sources used outside ZeroGen.
    """
    tool: DeclareUploadRequestTool
    workflow: NotRequired[dict[str, str | float | bool | list[Any] | dict[str, Any] | None]]
    """
    Untrusted JSON workflow, limited to 262144 serialized UTF-8 bytes.
    """
    prompt: NotRequired[str]
    externalRef: NotRequired[DeclareUploadRequestExternalRef]
    occurredAt: NotRequired[str]


class UpdateAssetRequest(TypedDict, closed=True):
    name: NotRequired[str]
    favorite: NotRequired[bool]
    """
    The organization's shared favorite
    """


AssetBatchRequestAssetId: TypeAlias = str


class AssetBatchRequest(TypedDict, closed=True):
    assetIds: list[AssetBatchRequestAssetId]
    """
    Up to 100 assets
    """


class RestoreFolderRequest(TypedDict, closed=True):
    eventId: str


class CreateFolderRequest(TypedDict, closed=True):
    projectId: str
    """
    The project to make the folder in
    """
    name: str
    parentId: NotRequired[str | None]
    """
    The parent folder, in the same project; omit or null for the project root
    """
    reuseExisting: NotRequired[bool]
    """
    When true, return the folder with this name that's already under the parent, with 200, instead of making another. Names match after Unicode NFC, case-sensitively; the oldest wins when several do
    """


class UpdateFolderRequest(TypedDict, closed=True):
    name: NotRequired[str]
    parentId: NotRequired[str | None]
    """
    The new parent folder, in the same project, or null for the project root
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


class CreateNamingPresetRequestDefinitionField(TypedDict, closed=True):
    id: str
    kind: Literal["shot", "take", "artist", "date", "version", "text", "folder"]
    label: str
    prefix: str
    padding: int
    step: int
    sequence: Literal["number", "letters"]
    artistFormat: Literal["initials", "compact", "hyphen", "underscore", "custom"]
    artistNameStyle: NotRequired[Literal["full", "initials"]]
    artistCase: NotRequired[Literal["preserve", "lower", "upper", "title"]]
    artistSeparator: NotRequired[str]
    dateFormat: str
    defaultValue: str
    folderRemoveSpaces: NotRequired[bool]


class CreateNamingPresetRequestDefinition(TypedDict, closed=True):
    delimiter: str
    fields: list[CreateNamingPresetRequestDefinitionField]


class CreateNamingPresetRequest(TypedDict, closed=True):
    projectId: str
    name: str
    definition: CreateNamingPresetRequestDefinition


class TransformAssetRequestRecipeExtractFrame(TypedDict, closed=True):
    timeSeconds: float
    """
    Where to take the frame, in seconds from the start of the video
    """


class TransformAssetRequestRecipeDespill(TypedDict, closed=True):
    screen: Literal["green", "blue"]
    """
    The screen color to remove from the subject
    """


class TransformAssetRequestRecipeLut(TypedDict, closed=True):
    lutId: str
    """
    A LUT from this organization
    """
    strength: NotRequired[int]
    """
    How much of the LUT to apply, as a percent; default 100
    """


class TransformAssetRequestRecipeAdjust(TypedDict, closed=True):
    exposure: NotRequired[int]
    """
    -100 is two stops darker, 100 two stops brighter; highlights can clip
    """
    brightness: NotRequired[int]
    """
    Moves the midtones; black and white stay where they are
    """
    contrast: NotRequired[int]
    """
    -100 halves the contrast around mid gray, 100 doubles it
    """
    saturation: NotRequired[int]
    """
    -100 is black and white, 100 doubles the saturation
    """
    temperature: NotRequired[int]
    """
    Below 0 is cooler, above 0 warmer
    """
    tint: NotRequired[int]
    """
    Below 0 is greener, above 0 more magenta
    """


class TransformAssetRequestRecipe(TypedDict, closed=True):
    extractFrame: TransformAssetRequestRecipeExtractFrame
    rotate: NotRequired[Literal[90, 180, 270]]
    """
    Turn the picture clockwise by this many degrees
    """
    flip: NotRequired[Literal["horizontal", "vertical"]]
    """
    Mirror the picture after any rotate: horizontal swaps left and right
    """
    inputColor: NotRequired[
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
    ]
    """
    What the footage is, which its metadata can't tell, so ask rather than guess. With it, adjust's exposure, temperature and tint run before any LUT on its curve and gamut, which can recover what the LUT would clip; without it, after
    """
    despill: NotRequired[TransformAssetRequestRecipeDespill]
    """
    Remove screen-colored spill from a green- or blue-screen shot, before any LUT. It changes every pixel of that color, so use it only on screen footage. The screen stays, turned neutral; this does not key it out
    """
    lut: NotRequired[TransformAssetRequestRecipeLut]
    """
    Apply a LUT. Use one whose inputColor matches the footage: a log LUT on Rec.709 footage looks wrong, and footage metadata can't tell. A video copy is tagged Rec.709
    """
    adjust: NotRequired[TransformAssetRequestRecipeAdjust]
    """
    Basic color correction, after any LUT, so it trims what the LUT gave. Each is a whole number from -100 to 100; 0 changes nothing
    """


class TransformAssetRequestRecipe1Crop(TypedDict, closed=True):
    x: int
    """
    Pixels from the picture's left edge to the area's
    """
    y: int
    """
    Pixels from the picture's top edge to the area's
    """
    width: int
    """
    The area's width, in pixels
    """
    height: int
    """
    The area's height, in pixels
    """


class TransformAssetRequestRecipe1Despill(TypedDict, closed=True):
    screen: Literal["green", "blue"]
    """
    The screen color to remove from the subject
    """


class TransformAssetRequestRecipe1Lut(TypedDict, closed=True):
    lutId: str
    """
    A LUT from this organization
    """
    strength: NotRequired[int]
    """
    How much of the LUT to apply, as a percent; default 100
    """


class TransformAssetRequestRecipe1Adjust(TypedDict, closed=True):
    exposure: NotRequired[int]
    """
    -100 is two stops darker, 100 two stops brighter; highlights can clip
    """
    brightness: NotRequired[int]
    """
    Moves the midtones; black and white stay where they are
    """
    contrast: NotRequired[int]
    """
    -100 halves the contrast around mid gray, 100 doubles it
    """
    saturation: NotRequired[int]
    """
    -100 is black and white, 100 doubles the saturation
    """
    temperature: NotRequired[int]
    """
    Below 0 is cooler, above 0 warmer
    """
    tint: NotRequired[int]
    """
    Below 0 is greener, above 0 more magenta
    """


class TransformAssetRequestRecipe1Resize(TypedDict, closed=True):
    maxEdge: int
    """
    Scale down proportionally so the longest edge is at most this many pixels; never enlarges
    """


class TransformAssetRequestRecipe1Convert(TypedDict, closed=True):
    format: Literal["png", "jpeg", "webp"]
    quality: NotRequired[int]
    """
    jpeg and webp only; default 90. An image already in the asked format that needs no resize is copied unchanged, so quality applies only when it is re-encoded
    """
    background: NotRequired[str]
    """
    jpeg only: the color that replaces transparency, such as #ffffff
    """


class TransformAssetRequestRecipe1(TypedDict, closed=True):
    rotate: NotRequired[Literal[90, 180, 270]]
    """
    Turn the picture clockwise by this many degrees
    """
    flip: NotRequired[Literal["horizontal", "vertical"]]
    """
    Mirror the picture after any rotate: horizontal swaps left and right
    """
    crop: NotRequired[TransformAssetRequestRecipe1Crop]
    """
    Keep this area of the upright image, turned and flipped as asked, within its width and height
    """
    inputColor: NotRequired[
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
    ]
    """
    What the footage is, which its metadata can't tell, so ask rather than guess. With it, adjust's exposure, temperature and tint run before any LUT on its curve and gamut, which can recover what the LUT would clip; without it, after
    """
    despill: NotRequired[TransformAssetRequestRecipe1Despill]
    """
    Remove screen-colored spill from a green- or blue-screen shot, before any LUT. It changes every pixel of that color, so use it only on screen footage. The screen stays, turned neutral; this does not key it out
    """
    lut: NotRequired[TransformAssetRequestRecipe1Lut]
    """
    Apply a LUT. Use one whose inputColor matches the footage: a log LUT on Rec.709 footage looks wrong, and footage metadata can't tell. A video copy is tagged Rec.709
    """
    adjust: NotRequired[TransformAssetRequestRecipe1Adjust]
    """
    Basic color correction, after any LUT, so it trims what the LUT gave. Each is a whole number from -100 to 100; 0 changes nothing
    """
    resize: NotRequired[TransformAssetRequestRecipe1Resize]
    convert: NotRequired[TransformAssetRequestRecipe1Convert]


class TransformAssetRequestRecipe2Trim(TypedDict, closed=True):
    startSeconds: float
    """
    Where the copy starts, in seconds
    """
    endSeconds: float
    """
    Where it ends, in seconds; at most 30 after startSeconds and within the video
    """


class TransformAssetRequestRecipe2FrameRate(TypedDict, closed=True):
    fps: int
    """
    The copy's frames per second. 23.976, 29.97 or 59.94 footage made 24, 30 or 60 keeps every frame and runs 0.1% shorter, its sound sped up to match; any other change repeats or drops frames and keeps the length
    """


class TransformAssetRequestRecipe2Lengthen(TypedDict, closed=True):
    toSeconds: float
    """
    The copy's length, longer than the clip after trim and speed
    """
    by: Literal["hold", "loop"]
    """
    hold: freeze the last frame, with silence. loop: play the clip again from its start, sound too
    """


class TransformAssetRequestRecipe2Crop(TypedDict, closed=True):
    x: int
    """
    Pixels from the picture's left edge to the area's
    """
    y: int
    """
    Pixels from the picture's top edge to the area's
    """
    width: int
    """
    The area's width, in pixels
    """
    height: int
    """
    The area's height, in pixels
    """


class TransformAssetRequestRecipe2Despill(TypedDict, closed=True):
    screen: Literal["green", "blue"]
    """
    The screen color to remove from the subject
    """


class TransformAssetRequestRecipe2Lut(TypedDict, closed=True):
    lutId: str
    """
    A LUT from this organization
    """
    strength: NotRequired[int]
    """
    How much of the LUT to apply, as a percent; default 100
    """


class TransformAssetRequestRecipe2Adjust(TypedDict, closed=True):
    exposure: NotRequired[int]
    """
    -100 is two stops darker, 100 two stops brighter; highlights can clip
    """
    brightness: NotRequired[int]
    """
    Moves the midtones; black and white stay where they are
    """
    contrast: NotRequired[int]
    """
    -100 halves the contrast around mid gray, 100 doubles it
    """
    saturation: NotRequired[int]
    """
    -100 is black and white, 100 doubles the saturation
    """
    temperature: NotRequired[int]
    """
    Below 0 is cooler, above 0 warmer
    """
    tint: NotRequired[int]
    """
    Below 0 is greener, above 0 more magenta
    """


class TransformAssetRequestRecipe2Resize(TypedDict, closed=True):
    maxEdge: int
    """
    Scale down proportionally so the longest edge is at most this many pixels; never enlarges
    """


class TransformAssetRequestRecipe2Convert(TypedDict, closed=True):
    format: Literal["mp4", "mov"]
    """
    mp4: H.264 8-bit 4:2:0, which every model and browser takes. mov: HEVC that keeps the source's 10-bit depth, 4:4:4 chroma, HDR and frame rate, for editing rather than as a model reference
    """
    maxBytes: NotRequired[int]
    """
    Keep the copy at most this many bytes, as a model's file limit asks: the bitrate is set from its length, and a copy that can't fit fails
    """


class TransformAssetRequestRecipe2(TypedDict, closed=True):
    trim: NotRequired[TransformAssetRequestRecipe2Trim]
    frameRate: NotRequired[TransformAssetRequestRecipe2FrameRate]
    removeAudio: NotRequired[Literal[True]]
    """
    Leave the audio out of the copy; without it, the copy keeps the first audio track
    """
    reverse: NotRequired[Literal[True]]
    """
    Play the clip backwards, sound too. It holds every frame in memory, so a long or large clip is refused
    """
    speed: NotRequired[float]
    """
    Play this many times as fast: 2 halves the length, 0.5 doubles it. The sound keeps its pitch, and the frame rate stays the source's unless frameRate sets it. Rounds to the hundredth
    """
    lengthen: NotRequired[TransformAssetRequestRecipe2Lengthen]
    rotate: NotRequired[Literal[90, 180, 270]]
    """
    Turn the picture clockwise by this many degrees
    """
    flip: NotRequired[Literal["horizontal", "vertical"]]
    """
    Mirror the picture after any rotate: horizontal swaps left and right
    """
    crop: NotRequired[TransformAssetRequestRecipe2Crop]
    """
    Keep this area of the upright picture, turned and flipped as asked, within its width and height. Each number rounds down to an even one, which video needs
    """
    inputColor: NotRequired[
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
    ]
    """
    What the footage is, which its metadata can't tell, so ask rather than guess. With it, adjust's exposure, temperature and tint run before any LUT on its curve and gamut, which can recover what the LUT would clip; without it, after
    """
    despill: NotRequired[TransformAssetRequestRecipe2Despill]
    """
    Remove screen-colored spill from a green- or blue-screen shot, before any LUT. It changes every pixel of that color, so use it only on screen footage. The screen stays, turned neutral; this does not key it out
    """
    lut: NotRequired[TransformAssetRequestRecipe2Lut]
    """
    Apply a LUT. Use one whose inputColor matches the footage: a log LUT on Rec.709 footage looks wrong, and footage metadata can't tell. A video copy is tagged Rec.709
    """
    adjust: NotRequired[TransformAssetRequestRecipe2Adjust]
    """
    Basic color correction, after any LUT, so it trims what the LUT gave. Each is a whole number from -100 to 100; 0 changes nothing
    """
    resize: NotRequired[TransformAssetRequestRecipe2Resize]
    convert: NotRequired[TransformAssetRequestRecipe2Convert]


class TransformAssetRequestRecipe3Trim(TypedDict, closed=True):
    startSeconds: float
    """
    Where the copy starts, in seconds
    """
    endSeconds: float
    """
    Where it ends, in seconds; at most 600 after startSeconds and within the source
    """


class TransformAssetRequestRecipe3Convert(TypedDict, closed=True):
    format: Literal["mp3", "wav", "aiff", "flac"]
    """
    mp3: 192 kbit/s, mono or stereo as the source is, which every model that takes audio accepts. wav, aiff and flac: lossless, at the source's sample rate and channels, 24-bit from a source deeper than 16, cut on the exact sample; for editing rather than as a model reference
    """


class TransformAssetRequestRecipe3(TypedDict, closed=True):
    trim: NotRequired[TransformAssetRequestRecipe3Trim]
    convert: NotRequired[TransformAssetRequestRecipe3Convert]
    """
    The output; an MP3 when left out. On a video, give it to ask for audio
    """


class TransformAssetRequest(TypedDict, closed=True):
    recipe: (
        TransformAssetRequestRecipe
        | TransformAssetRequestRecipe1
        | TransformAssetRequestRecipe2
        | TransformAssetRequestRecipe3
    )
    projectId: NotRequired[str]
    """
    The project the copy goes into; the source asset's project when omitted
    """
    folderId: NotRequired[str | None]
    """
    A folder in that project to also add the copy to; null or omitted for Unfiled
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
    name: NotRequired[str]
    description: NotRequired[str | None]
    """
    null or an empty string clears it
    """
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


class CreateAttachmentRequest(TypedDict, closed=True):
    projectId: str
    folderId: NotRequired[str]
    clipId: NotRequired[str]
    title: str
    """
    Verbatim title: 1–200 characters on one line, without surrounding whitespace.
    """
    body: str
    """
    Verbatim attachment text: 1–8,000 Unicode characters.
    """


class ReviseAttachmentRequest(TypedDict, closed=True):
    expectedVersion: int
    body: str


class RestoreAttachmentRequest(TypedDict, closed=True):
    version: int
    expectedVersion: int
