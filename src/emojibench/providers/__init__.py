"""Image-provider selection and public contracts."""

import os
from collections.abc import Mapping

from emojibench.providers.base import (
    CostLimitError,
    GeneratedAsset,
    ImageProvider,
    ProviderConfigurationError,
    ProviderError,
)
from emojibench.providers.mock import MockProvider
from emojibench.providers.openai import ApiCallGuard, OpenAIProvider


def get_provider(
    provider: str | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> ImageProvider:
    """Select an image provider from an override or the environment.

    Args:
        provider: Optional explicit provider name.
        environ: Environment values. The process environment is the default.

    Returns:
        A configured image provider. The default is the offline mock.

    Raises:
        ProviderConfigurationError: If the provider name or settings are invalid.
    """
    selected_environ = os.environ if environ is None else environ
    selected_name = (
        provider
        if provider is not None
        else selected_environ.get("EMOJIBENCH_PROVIDER", "mock")
    ).strip().lower()
    if not selected_name:
        selected_name = "mock"
    if selected_name == "mock":
        return MockProvider()
    if selected_name == "openai":
        return OpenAIProvider(environ=selected_environ)
    msg = f"Unknown provider '{selected_name}'. Use 'mock' or 'openai'."
    raise ProviderConfigurationError(msg)


__all__ = [
    "ApiCallGuard",
    "CostLimitError",
    "GeneratedAsset",
    "ImageProvider",
    "MockProvider",
    "OpenAIProvider",
    "ProviderConfigurationError",
    "ProviderError",
    "get_provider",
]
