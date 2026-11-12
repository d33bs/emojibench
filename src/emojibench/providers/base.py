"""Shared image-provider contracts and provenance helpers."""

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from emojibench.catalog import CatalogError, asset_by_id, load_catalog
from emojibench.combinations import normalize_pair
from emojibench.models import Asset


class ProviderError(RuntimeError):
    """An image provider could not generate an asset."""


class ProviderConfigurationError(ProviderError):
    """Image-provider configuration is absent or invalid."""


class CostLimitError(ProviderError):
    """A paid request would exceed the process call limit."""


@dataclass(frozen=True)
class GeneratedAsset:
    """An asset record and its generated image bytes.

    Attributes:
        asset: Draft asset with full generation provenance.
        image_bytes: Encoded image content.
    """

    asset: Asset
    image_bytes: bytes


class ImageProvider(ABC):
    """Generate an image from two catalog asset identifiers."""

    name: str
    model: str

    @abstractmethod
    def generate(self, first: str, second: str) -> GeneratedAsset:
        """Generate one draft asset.

        Args:
            first: First catalog asset identifier.
            second: Second catalog asset identifier.

        Returns:
            The generated image and its draft asset record.

        Raises:
            ProviderError: If validation or generation fails.
        """


def validate_inputs(first: str, second: str) -> tuple[str, str]:
    """Validate and normalize two catalog identifiers.

    Args:
        first: First catalog asset identifier.
        second: Second catalog asset identifier.

    Returns:
        The identifiers in canonical order.

    Raises:
        ProviderError: If either identifier is not in the catalog.
    """
    try:
        assets = load_catalog()
        asset_by_id(first, assets)
        asset_by_id(second, assets)
    except CatalogError as error:
        raise ProviderError(str(error)) from error
    return normalize_pair(first, second)


def creative_brief(first: str, second: str) -> str:
    """Build the original-art brief for a normalized pair.

    Args:
        first: First catalog asset identifier.
        second: Second catalog asset identifier.

    Returns:
        A concise provider prompt with style and safety constraints.
    """
    assets = load_catalog()
    first_name = asset_by_id(first, assets).name.lower()
    second_name = asset_by_id(second, assets).name.lower()
    return (
        "Create an original illustration that combines "
        f"a {first_name} and a {second_name} as one recognizable character. "
        "Use a flat, friendly cartoon style with five colors or fewer, an opaque "
        "solid pastel background, no text, and a square canvas. This is a playful "
        "creative analogy, not scientific evidence. Do not copy existing emoji artwork."
    )


def build_generated_asset(
    *,
    first: str,
    second: str,
    provider: str,
    model: str,
    settings: dict[str, Any],
    prompt: str,
    image_bytes: bytes,
    source: str,
    license_name: str,
    rights_status: str,
    suffix: str = ".png",
) -> GeneratedAsset:
    """Create a draft asset and complete provenance from image bytes.

    Args:
        first: First normalized input identifier.
        second: Second normalized input identifier.
        provider: Provider name.
        model: Provider model identifier.
        settings: Output settings sent to the provider.
        prompt: Creative brief sent to the provider.
        image_bytes: Encoded generated image.
        source: Human-readable generation source.
        license_name: License or rights-review label.
        rights_status: Current publication-rights status.
        suffix: Image file suffix.

    Returns:
        The generated image and its draft asset record.
    """
    digest = hashlib.sha256(image_bytes).hexdigest()
    asset_id = f"generated-{provider}-{digest[:16]}"
    metadata = {
        "inputs": [first, second],
        "creative_brief": prompt,
        "prompt": prompt,
        "provider": provider,
        "model": model,
        "settings": settings,
        "generated_at": datetime.now(UTC).isoformat(),
        "output_checksum": f"sha256:{digest}",
        "rights_status": rights_status,
        "license": license_name,
        "review_state": "draft",
    }
    asset = Asset(
        id=asset_id,
        name=f"{first.replace('-', ' ').title()} + {second.replace('-', ' ').title()}",
        category="generated",
        tags=[first, second, provider],
        image_uri=f"generated/{asset_id}{suffix}",
        source=source,
        license=license_name,
        kind="generated",
        status="draft",
        generation_metadata=metadata,
        scientific_metadata={
            "content_type": "generated illustration",
            "evidence_status": "creative_analogy",
        },
    )
    return GeneratedAsset(asset=asset, image_bytes=image_bytes)
