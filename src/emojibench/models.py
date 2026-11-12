"""Validated data models for emojibench content."""

from datetime import datetime
from pathlib import PurePosixPath
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    ValidationInfo,
    field_validator,
)

Slug = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    ),
]
NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
AssetKind = Literal["original", "generated", "scientific"]
ReviewStatus = Literal["draft", "approved", "rejected"]
EvidenceStatus = Literal["observation", "interpretation", "creative_analogy"]


class StrictModel(BaseModel):
    """Base model that rejects unknown fields."""

    model_config = ConfigDict(extra="forbid")


class MicroscopySource(StrictModel):
    """A microscopy source reference for a scientific asset.

    Attributes:
        dataset: Name of the source dataset.
        image_uri: Path or identifier of the source image inside the
            dataset.
        attribution: Who created the source image.
        license: License identifier for the source image.
        crop: Optional crop box as x, y, width, height in pixels.
        object_id: Optional segmentation object identifier.
        dimensions: Source image dimensions in pixels as width, height.
        measurements: Optional per-object measurements from analysis.
        references: Optional scientific references for the source.
    """

    dataset: NonEmptyString
    image_uri: NonEmptyString
    attribution: NonEmptyString
    license: NonEmptyString
    crop: tuple[int, int, int, int] | None = None
    object_id: str | int | None = None
    dimensions: tuple[int, int] | None = None
    measurements: dict[str, Any] | None = None
    references: list[NonEmptyString] | None = None


class Asset(StrictModel):
    """A catalog image and its provenance metadata.

    Attributes:
        id: Stable slug for the asset.
        name: Human-readable asset name.
        category: Catalog group name.
        tags: Search terms for the asset.
        image_uri: Local path to the image.
        source: Creator or source description.
        license: License identifier for the image.
        kind: Origin type for the image.
        status: Human review state.
        generation_metadata: Details for generated or mock images.
        scientific_metadata: Scientific source and review details.
        schema_version: Version of this data schema.
    """

    id: Slug
    name: NonEmptyString
    category: NonEmptyString
    tags: list[NonEmptyString]
    image_uri: NonEmptyString
    source: NonEmptyString
    license: NonEmptyString
    kind: AssetKind
    status: ReviewStatus
    generation_metadata: dict[str, Any] | None = None
    scientific_metadata: dict[str, Any] | None = None
    schema_version: NonEmptyString = "1.0"

    @field_validator("image_uri")
    @classmethod
    def image_uri_must_be_local(_cls, value: str) -> str:
        """Reject remote and parent-relative image paths.

        Args:
            value: Image path from the model input.

        Returns:
            The validated local image path.

        Raises:
            ValueError: If the path is remote, absolute, or parent-relative.
        """
        path = PurePosixPath(value)
        if "://" in value or value.startswith("//"):
            msg = "image_uri must be a local path"
            raise ValueError(msg)
        if path.is_absolute() or ".." in path.parts:
            msg = "image_uri must stay inside the catalog directory"
            raise ValueError(msg)
        return value

    @field_validator("scientific_metadata")
    @classmethod
    def scientific_kind_needs_microscopy_source(
        _cls, value: dict[str, Any] | None, info: ValidationInfo
    ) -> dict[str, Any] | None:
        """Require a valid microscopy source on scientific assets.

        Args:
            value: Scientific metadata from the model input.
            info: Validation context with the sibling field values.

        Returns:
            The validated scientific metadata.

        Raises:
            ValueError: If a scientific asset lacks a microscopy source.
        """
        kind = info.data.get("kind")
        if kind != "scientific":
            return value
        if value is None:
            msg = "scientific assets need scientific_metadata with a source"
            raise ValueError(msg)
        try:
            MicroscopySource.model_validate(value.get("microscopy_source"))
        except ValidationError as error:
            msg = f"invalid microscopy source: {error}"
            raise ValueError(msg) from error
        return value


class Combination(StrictModel):
    """A deterministic combination of two catalog assets.

    The model stores ``input_ids`` in sorted order. Therefore, ``a+b`` and
    ``b+a`` describe the same combination.

    Attributes:
        id: Stable slug derived from the normalized input pair.
        input_ids: Canonical pair of source asset identifiers.
        output_asset_id: Optional identifier for a saved output asset.
        status: Human review state.
        created_at: Time when the record was created.
        evaluation: Optional evaluation data for the output.
    """

    id: Slug
    input_ids: tuple[Slug, Slug]
    output_asset_id: Slug | None = None
    status: ReviewStatus
    created_at: datetime
    evaluation: dict[str, Any] | None = None

    @field_validator("input_ids")
    @classmethod
    def normalize_input_ids(_cls, value: tuple[str, str]) -> tuple[str, str]:
        """Put source identifiers in canonical order.

        Args:
            value: Pair of validated source identifiers.

        Returns:
            The sorted source pair.
        """
        first, second = value
        return (first, second) if first <= second else (second, first)

    @field_validator("created_at")
    @classmethod
    def created_at_must_include_timezone(_cls, value: datetime) -> datetime:
        """Require an unambiguous creation time.

        Args:
            value: Creation time from the model input.

        Returns:
            The validated creation time.

        Raises:
            ValueError: If the time has no UTC offset.
        """
        if value.tzinfo is None or value.utcoffset() is None:
            msg = "created_at must include a timezone"
            raise ValueError(msg)
        return value


class StoryPanel(StrictModel):
    """One ordered panel in a story.

    Attributes:
        asset_id: Asset shown in the panel.
        caption: Text shown with the panel.
        references: Optional sources for the panel content.
        evidence_status: Scientific evidence category for the caption.
    """

    asset_id: Slug
    caption: NonEmptyString
    references: list[NonEmptyString] | None = None
    evidence_status: EvidenceStatus


class Story(StrictModel):
    """An ordered visual story for a named audience.

    Attributes:
        id: Stable slug for the story.
        title: Human-readable story title.
        audience: Intended reader group.
        panels: Ordered story panels.
        status: Human review state.
        created_at: Time when the story was created.
        schema_version: Version of this data schema.
    """

    id: Slug
    title: NonEmptyString
    audience: NonEmptyString
    panels: list[StoryPanel] = Field(min_length=1)
    status: ReviewStatus
    created_at: datetime
    schema_version: NonEmptyString = "1.0"

    @field_validator("created_at")
    @classmethod
    def created_at_must_include_timezone(_cls, value: datetime) -> datetime:
        """Require an unambiguous creation time.

        Args:
            value: Creation time from the model input.

        Returns:
            The validated creation time.

        Raises:
            ValueError: If the time has no UTC offset.
        """
        if value.tzinfo is None or value.utcoffset() is None:
            msg = "created_at must include a timezone"
            raise ValueError(msg)
        return value
