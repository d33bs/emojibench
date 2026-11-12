"""Tests for offline and paid image providers."""

import base64
from pathlib import Path

import httpx
import pytest

from emojibench.combinations import write_preview
from emojibench.providers import (
    ApiCallGuard,
    CostLimitError,
    MockProvider,
    OpenAIProvider,
    ProviderConfigurationError,
    ProviderError,
    get_provider,
)


def _preview_bytes(tmp_path: Path) -> bytes:
    """Return a valid deterministic PNG for an API response."""
    path = tmp_path / "response.png"
    write_preview("macrophage", "superhero", path)
    return path.read_bytes()


def test_default_provider_is_deterministic_offline_mock() -> None:
    """An empty configuration selects the offline mock provider."""
    provider = get_provider(environ={})

    first = provider.generate("macrophage", "superhero")
    second = provider.generate("superhero", "macrophage")

    assert isinstance(provider, MockProvider)
    assert first.image_bytes == second.image_bytes
    assert first.asset.id == second.asset.id
    assert first.asset.status == "draft"
    assert first.asset.generation_metadata is not None
    assert first.asset.generation_metadata["inputs"] == [
        "macrophage",
        "superhero",
    ]
    assert first.asset.generation_metadata["provider"] == "mock"
    assert first.asset.generation_metadata["model"] == "mock"
    assert first.asset.generation_metadata["review_state"] == "draft"
    assert first.asset.generation_metadata["output_checksum"].startswith("sha256:")


def test_provider_override_and_unknown_provider() -> None:
    """An explicit provider wins and unknown names fail clearly."""
    assert isinstance(
        get_provider("mock", environ={"EMOJIBENCH_PROVIDER": "openai"}),
        MockProvider,
    )

    with pytest.raises(ProviderConfigurationError, match="Unknown provider 'other'"):
        get_provider("other", environ={})


def test_openai_provider_requires_api_key() -> None:
    """The paid provider does not start without an API key."""
    with pytest.raises(
        ProviderConfigurationError,
        match="OPENAI_API_KEY is required",
    ):
        get_provider("openai", environ={})


def test_cost_guard_blocks_calls_above_limit() -> None:
    """The process call guard rejects a call above its fixed limit."""
    guard = ApiCallGuard(limit=1)

    guard.consume()

    with pytest.raises(CostLimitError, match="API call limit of 1 was reached"):
        guard.consume()


def test_openai_provider_decodes_response_and_records_provenance(
    tmp_path: Path,
) -> None:
    """A successful API response becomes a draft PNG asset."""
    image = base64.b64encode(_preview_bytes(tmp_path)).decode("ascii")

    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/images/generations"
        assert request.headers["Authorization"] == "Bearer secret"
        return httpx.Response(200, json={"data": [{"b64_json": image}]})

    provider = OpenAIProvider(
        environ={
            "OPENAI_API_KEY": "secret",
            "EMOJIBENCH_API_RETRIES": "0",
        },
        guard=ApiCallGuard(limit=1),
        transport=httpx.MockTransport(respond),
    )

    result = provider.generate("macrophage", "superhero")

    assert result.image_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    assert result.asset.status == "draft"
    assert result.asset.generation_metadata is not None
    assert result.asset.generation_metadata["provider"] == "openai"
    assert result.asset.generation_metadata["model"] == "gpt-image-2.5-flare"
    assert result.asset.generation_metadata["settings"] == {
        "format": "png",
        "quality": "low",
        "size": "1024x1024",
    }


def test_openai_provider_surfaces_api_error() -> None:
    """A rejected request includes the service cause in its error."""

    def reject(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"error": {"message": "prompt was rejected"}},
        )

    provider = OpenAIProvider(
        environ={
            "OPENAI_API_KEY": "secret",
            "EMOJIBENCH_API_RETRIES": "0",
        },
        guard=ApiCallGuard(limit=1),
        transport=httpx.MockTransport(reject),
    )

    with pytest.raises(ProviderError, match="prompt was rejected"):
        provider.generate("macrophage", "superhero")


def test_openai_provider_surfaces_timeout() -> None:
    """A timed-out request stops after the configured retry count."""

    def time_out(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow endpoint", request=request)

    provider = OpenAIProvider(
        environ={
            "OPENAI_API_KEY": "secret",
            "EMOJIBENCH_API_RETRIES": "0",
            "EMOJIBENCH_API_TIMEOUT_SECONDS": "1",
        },
        guard=ApiCallGuard(limit=1),
        transport=httpx.MockTransport(time_out),
    )

    with pytest.raises(ProviderError, match="timed out.*slow endpoint"):
        provider.generate("macrophage", "superhero")


def test_paid_call_limit_counts_real_requests(tmp_path: Path) -> None:
    """The paid provider consumes one guard slot for each HTTP request."""
    image = base64.b64encode(_preview_bytes(tmp_path)).decode("ascii")

    def respond(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"b64_json": image}]})

    provider = OpenAIProvider(
        environ={
            "OPENAI_API_KEY": "secret",
            "EMOJIBENCH_API_RETRIES": "0",
        },
        guard=ApiCallGuard(limit=1),
        transport=httpx.MockTransport(respond),
    )
    provider.generate("macrophage", "superhero")

    with pytest.raises(CostLimitError, match="API call limit of 1 was reached"):
        provider.generate("macrophage", "superhero")


@pytest.mark.parametrize("provider_name", ["mock", "openai"])
def test_provider_rejects_invalid_asset_ids(provider_name: str) -> None:
    """Each provider validates source identifiers before generation."""
    environ = {"OPENAI_API_KEY": "secret"} if provider_name == "openai" else {}
    provider = get_provider(provider_name, environ=environ)

    with pytest.raises(ProviderError, match="Unknown asset id 'missing'"):
        provider.generate("missing", "superhero")
