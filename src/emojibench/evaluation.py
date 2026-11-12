"""Deterministic checks for generated PNG and SVG assets."""

import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree

from PIL import Image, UnidentifiedImageError

from emojibench.generation import AssetStore, GenerationError
from emojibench.models import Asset, NonEmptyString, StrictModel

ALLOWED_IMAGE_TYPES = {".png": "PNG", ".svg": "SVG"}
REQUIRED_METADATA = {
    "inputs",
    "creative_brief",
    "prompt",
    "provider",
    "model",
    "settings",
    "generated_at",
    "output_checksum",
    "rights_status",
    "license",
    "review_state",
}
DIMENSION_PATTERN = re.compile(r"^(\d+)(?:\.0+)?(?:px)?$")
SIZE_PATTERN = re.compile(r"^(\d+)x(\d+)$")


class EvaluationCheck(StrictModel):
    """One deterministic asset check.

    Attributes:
        name: Stable check name.
        passed: Whether the check passed.
        detail: Human-readable result detail.
    """

    name: NonEmptyString
    passed: bool
    detail: NonEmptyString


class EvaluationResult(StrictModel):
    """Complete deterministic evaluation report.

    Attributes:
        path: Evaluated image path.
        passed: Whether all checks passed.
        evaluated_at: Time of evaluation.
        checks: Ordered check results.
    """

    path: NonEmptyString
    passed: bool
    evaluated_at: datetime
    checks: list[EvaluationCheck]


def evaluate_asset(
    path: str | Path,
    *,
    store_root: str | Path | None = None,
) -> EvaluationResult:
    """Evaluate an image and record the result without approving it.

    Args:
        path: Generated PNG or SVG path.
        store_root: Optional local generation store root.

    Returns:
        A deterministic pass or fail report.
    """
    image_path = Path(path)
    checks: list[EvaluationCheck] = []
    file_exists = image_path.is_file()
    checks.append(
        EvaluationCheck(
            name="file_exists",
            passed=file_exists,
            detail=(
                f"File exists: {image_path}"
                if file_exists
                else f"File does not exist: {image_path}"
            ),
        )
    )

    suffix = image_path.suffix.lower()
    allowed = suffix in ALLOWED_IMAGE_TYPES
    checks.append(
        EvaluationCheck(
            name="allowed_image_type",
            passed=allowed,
            detail=(
                f"Allowed image type: {suffix}"
                if allowed
                else f"Image type is not allowed: {suffix or '(none)'}"
            ),
        )
    )

    asset = _load_metadata(image_path) if file_exists else None
    checks.append(
        EvaluationCheck(
            name="metadata_present",
            passed=asset is not None,
            detail=(
                "Generated asset metadata is present."
                if asset is not None
                else "Generated asset metadata is absent or invalid."
            ),
        )
    )
    metadata = asset.generation_metadata if asset is not None else None
    missing_metadata = (
        sorted(REQUIRED_METADATA - metadata.keys())
        if metadata is not None
        else sorted(REQUIRED_METADATA)
    )
    checks.append(
        EvaluationCheck(
            name="required_metadata",
            passed=not missing_metadata,
            detail=(
                "All required provenance fields are present."
                if not missing_metadata
                else f"Missing provenance fields: {', '.join(missing_metadata)}"
            ),
        )
    )

    image_bytes = b""
    dimensions: tuple[int, int] | None = None
    decode_detail = "Image could not be decoded."
    decoded = False
    if file_exists and allowed:
        try:
            image_bytes = image_path.read_bytes()
            dimensions = _decode_dimensions(image_path, suffix)
            decoded = True
            decode_detail = (
                f"Decoded {ALLOWED_IMAGE_TYPES[suffix]} image: "
                f"{dimensions[0]}x{dimensions[1]}"
            )
        except (OSError, ValueError, ElementTree.ParseError, UnidentifiedImageError) as error:
            decode_detail = f"Image could not be decoded: {error}"
    checks.append(
        EvaluationCheck(
            name="decodes",
            passed=decoded,
            detail=decode_detail,
        )
    )

    expected_dimensions = _expected_dimensions(metadata)
    dimensions_match = dimensions is not None and dimensions == expected_dimensions
    checks.append(
        EvaluationCheck(
            name="expected_dimensions",
            passed=dimensions_match,
            detail=(
                f"Image dimensions match {expected_dimensions[0]}x{expected_dimensions[1]}."
                if dimensions_match and expected_dimensions is not None
                else _dimension_error(dimensions, expected_dimensions)
            ),
        )
    )

    actual_checksum = (
        f"sha256:{hashlib.sha256(image_bytes).hexdigest()}" if image_bytes else None
    )
    expected_checksum = (
        metadata.get("output_checksum") if metadata is not None else None
    )
    checksum_matches = actual_checksum is not None and actual_checksum == expected_checksum
    checks.append(
        EvaluationCheck(
            name="content_checksum",
            passed=checksum_matches,
            detail=(
                "Content checksum matches the provenance record."
                if checksum_matches
                else "Content checksum does not match the provenance record."
            ),
        )
    )

    evaluated_at = datetime.now(UTC)
    result = EvaluationResult(
        path=str(image_path),
        passed=all(item.passed for item in checks),
        evaluated_at=evaluated_at,
        checks=checks,
    )
    if asset is not None:
        _record_evaluation(asset, image_path, result, store_root)
    return result


def _load_metadata(image_path: Path) -> Asset | None:
    """Load a generated asset sidecar when it is valid."""
    sidecar = image_path.with_suffix(".json")
    if not sidecar.is_file():
        return None
    try:
        return AssetStore.load_sidecar(sidecar)
    except GenerationError:
        return None


def _decode_dimensions(path: Path, suffix: str) -> tuple[int, int]:
    """Decode an image and return its dimensions."""
    if suffix == ".png":
        with Image.open(path) as image:
            if image.format != "PNG":
                msg = f"Expected PNG content, received {image.format}."
                raise ValueError(msg)
            dimensions = image.size
            image.verify()
        with Image.open(path) as image:
            image.load()
        return dimensions

    root = ElementTree.fromstring(path.read_bytes())
    if root.tag.rsplit("}", 1)[-1] != "svg":
        msg = "The XML root is not an SVG element."
        raise ValueError(msg)
    width = _svg_dimension(root.get("width"))
    height = _svg_dimension(root.get("height"))
    if width is not None and height is not None:
        return width, height
    view_box = root.get("viewBox", "").split()
    if len(view_box) == 4:
        try:
            return int(float(view_box[2])), int(float(view_box[3]))
        except ValueError as error:
            msg = "The SVG viewBox has invalid dimensions."
            raise ValueError(msg) from error
    msg = "The SVG does not define numeric dimensions."
    raise ValueError(msg)


def _svg_dimension(value: str | None) -> int | None:
    """Convert a numeric SVG width or height into an integer."""
    if value is None:
        return None
    match = DIMENSION_PATTERN.fullmatch(value.strip())
    return int(float(match.group(1))) if match else None


def _expected_dimensions(metadata: dict[str, object] | None) -> tuple[int, int] | None:
    """Read expected dimensions from generation settings."""
    if metadata is None:
        return None
    settings = metadata.get("settings")
    if not isinstance(settings, dict):
        return None
    size = settings.get("size")
    if not isinstance(size, str):
        return None
    match = SIZE_PATTERN.fullmatch(size)
    return (int(match.group(1)), int(match.group(2))) if match else None


def _dimension_error(
    actual: tuple[int, int] | None,
    expected: tuple[int, int] | None,
) -> str:
    """Build a clear dimension mismatch detail."""
    if expected is None:
        return "Expected dimensions are absent or invalid in provenance."
    if actual is None:
        return "Image dimensions could not be decoded."
    return (
        f"Image dimensions are {actual[0]}x{actual[1]}; "
        f"expected {expected[0]}x{expected[1]}."
    )


def _record_evaluation(
    asset: Asset,
    image_path: Path,
    result: EvaluationResult,
    store_root: str | Path | None,
) -> None:
    """Write evaluation metadata without changing the review state."""
    metadata = dict(asset.generation_metadata or {})
    metadata["evaluation"] = result.model_dump(mode="json")
    updated = Asset.model_validate(
        {**asset.model_dump(), "generation_metadata": metadata}
    )
    selected_root = (
        Path(store_root)
        if store_root is not None
        else image_path.parent.parent
    )
    store = AssetStore(selected_root)
    try:
        store.get(asset.id)
    except ValueError:
        image_path.with_suffix(".json").write_text(
            updated.model_dump_json(indent=2),
            encoding="utf-8",
        )
    else:
        store.update(updated)
