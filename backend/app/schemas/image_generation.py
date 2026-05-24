from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


ImageSize = Literal[
    "1024x1024",
    "1536x1024",
    "1024x1536",
    "2048x1152",
    "1152x2048",
    "auto",
]
ImageQuality = Literal["high", "medium", "low", "auto"]
ImageReferenceType = Literal["persona", "product", "location"]


class ImageGenerateRequest(BaseModel):
    project_id: int | None = Field(default=None, ge=1)
    prompt: str = Field(min_length=1, max_length=2000)
    n: int = Field(default=1, ge=1, le=10)
    size: ImageSize = "1536x1024"
    quality: ImageQuality = "medium"


class ImageReferenceInput(BaseModel):
    reference_image_type: ImageReferenceType
    source_image_base64: str = Field(min_length=1, max_length=20_000_000)
    source_image_mime: str = Field(default="image/png", min_length=1, max_length=80)
    source_image_filename: str = Field(default="source.png", min_length=1, max_length=160)


class ImageEditRequest(ImageGenerateRequest):
    source_image_base64: str | None = Field(default=None, min_length=1, max_length=20_000_000)
    source_image_mime: str = Field(default="image/png", min_length=1, max_length=80)
    source_image_filename: str = Field(default="source.png", min_length=1, max_length=160)
    reference_image_types: list[ImageReferenceType] = Field(default_factory=lambda: ["product"], min_length=1, max_length=3)
    reference_images: list[ImageReferenceInput] = Field(default_factory=list, max_length=9)

    @model_validator(mode="after")
    def validate_reference_images(self) -> "ImageEditRequest":
        total_images = len(self.reference_images) + (1 if self.source_image_base64 else 0)
        if total_images < 1:
            raise ValueError("图生图至少要上传一张参考图")

        counts = {"persona": 0, "product": 0, "location": 0}
        for image in self.reference_images:
            counts[image.reference_image_type] += 1
        if self.source_image_base64:
            for reference_type in self.reference_image_types:
                counts[reference_type] += 1

        over_limit = [key for key, count in counts.items() if count > 3]
        if over_limit:
            raise ValueError("每类参考图最多上传 3 张")
        return self


class GeneratedImage(BaseModel):
    b64_json: str | None = None
    url: str | None = None
    data_url: str | None = None
    asset_id: int | None = None
    oss_object_key: str | None = None
    mime_type: str | None = None
    signed_url_expires_at: int | None = None


class ImageGenerateResponse(BaseModel):
    provider: str
    model: str
    images: list[GeneratedImage]
    usage: dict[str, Any] = Field(default_factory=dict)
    latency_ms: int


class ImagePromptEnhanceRequest(BaseModel):
    project_id: int | None = Field(default=None, ge=1)
    prompt: str = Field(min_length=1, max_length=2000)
    mode: Literal["text", "image"] = "text"
    size: ImageSize = "1024x1536"
    quality: ImageQuality = "medium"


class ImagePromptEnhanceResponse(BaseModel):
    enhanced_prompt: str
    subject: str
    removed_terms: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
