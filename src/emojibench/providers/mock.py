"""Deterministic offline image provider."""

from emojibench.combinations import _render_png
from emojibench.providers.base import (
    GeneratedAsset,
    ImageProvider,
    build_generated_asset,
    creative_brief,
    validate_inputs,
)


class MockProvider(ImageProvider):
    """Create a labeled local placeholder without a network request."""

    name = "mock"
    model = "mock"

    def generate(self, first: str, second: str) -> GeneratedAsset:
        """Create one deterministic mock preview.

        Args:
            first: First catalog asset identifier.
            second: Second catalog asset identifier.

        Returns:
            A draft asset and deterministic PNG bytes.

        Raises:
            ProviderError: If either input identifier is invalid.
        """
        first_id, second_id = validate_inputs(first, second)
        image_bytes = _render_png(first_id, second_id)
        prompt = creative_brief(first_id, second_id)
        return build_generated_asset(
            first=first_id,
            second=second_id,
            provider=self.name,
            model=self.model,
            settings={
                "format": "png",
                "preview_type": "deterministic placeholder",
                "size": "512x320",
            },
            prompt=prompt,
            image_bytes=image_bytes,
            source="emojibench deterministic mock provider",
            license_name="BSD-3-Clause",
            rights_status="Original project inputs under the BSD-3-Clause license.",
        )
