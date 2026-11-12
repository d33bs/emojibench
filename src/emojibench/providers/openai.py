"""OpenAI Images API provider with bounded paid calls."""

import base64
import binascii
import os
import threading
from collections.abc import Mapping
from typing import Final

import httpx

from emojibench.providers.base import (
    CostLimitError,
    GeneratedAsset,
    ImageProvider,
    ProviderConfigurationError,
    ProviderError,
    build_generated_asset,
    creative_brief,
    validate_inputs,
)

DEFAULT_MODEL: Final = "gpt-image-2.5-flare"
DEFAULT_MAX_API_CALLS: Final = 2
DEFAULT_TIMEOUT_SECONDS: Final = 120.0
DEFAULT_RETRIES: Final = 1
MAX_API_CALLS: Final = 100
MAX_TIMEOUT_SECONDS: Final = 300.0
MAX_RETRIES: Final = 2
OPENAI_IMAGES_URL: Final = "https://api.openai.com/v1/images/generations"
PNG_SIGNATURE: Final = b"\x89PNG\r\n\x1a\n"

SUPPORTED_MODELS: Final = {
    "gpt-image-1-mini",
    "gpt-image-1.5",
    "gpt-image-2",
    "gpt-image-2.5-flare",
    "gpt-image-2.5-sunburst",
    "gpt-image-2.6-flare",
    "gpt-image-2.6-sunburst",
    "chatgpt-image-latest",
}
SUPPORTED_SIZES: Final = {"1024x1024", "1536x1024", "1024x1536"}
SUPPORTED_QUALITIES: Final = {"low", "medium", "high"}


class ApiCallGuard:
    """Count paid API calls for one process.

    Args:
        limit: Maximum number of paid HTTP requests.
    """

    def __init__(self, limit: int) -> None:
        """Initialize the fixed call limit."""
        if not 0 <= limit <= MAX_API_CALLS:
            msg = f"API call limit must be between 0 and {MAX_API_CALLS}."
            raise ProviderConfigurationError(msg)
        self.limit = limit
        self.used = 0
        self._lock = threading.Lock()

    def consume(self) -> None:
        """Reserve one paid request before network access.

        Raises:
            CostLimitError: If no paid calls remain.
        """
        with self._lock:
            if self.used >= self.limit:
                msg = (
                    f"The API call limit of {self.limit} was reached. "
                    "Increase EMOJIBENCH_MAX_API_CALLS to allow another paid call."
                )
                raise CostLimitError(msg)
            self.used += 1


_process_guard: ApiCallGuard | None = None
_process_guard_lock = threading.Lock()


def _integer_setting(
    environ: Mapping[str, str],
    name: str,
    default: int,
    maximum: int,
) -> int:
    """Read a bounded nonnegative integer setting."""
    raw_value = environ.get(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as error:
        msg = f"{name} must be an integer between 0 and {maximum}."
        raise ProviderConfigurationError(msg) from error
    if not 0 <= value <= maximum:
        msg = f"{name} must be between 0 and {maximum}."
        raise ProviderConfigurationError(msg)
    return value


def _timeout_setting(environ: Mapping[str, str]) -> float:
    """Read the bounded request timeout setting."""
    name = "EMOJIBENCH_API_TIMEOUT_SECONDS"
    raw_value = environ.get(name, str(DEFAULT_TIMEOUT_SECONDS))
    try:
        value = float(raw_value)
    except ValueError as error:
        msg = f"{name} must be a number between 1 and {MAX_TIMEOUT_SECONDS}."
        raise ProviderConfigurationError(msg) from error
    if not 1 <= value <= MAX_TIMEOUT_SECONDS:
        msg = f"{name} must be between 1 and {MAX_TIMEOUT_SECONDS}."
        raise ProviderConfigurationError(msg)
    return value


def _default_process_guard(environ: Mapping[str, str]) -> ApiCallGuard:
    """Return the single paid-call guard for this process."""
    global _process_guard  # noqa: PLW0603
    with _process_guard_lock:
        if _process_guard is None:
            limit = _integer_setting(
                environ,
                "EMOJIBENCH_MAX_API_CALLS",
                DEFAULT_MAX_API_CALLS,
                MAX_API_CALLS,
            )
            _process_guard = ApiCallGuard(limit)
        return _process_guard


class OpenAIProvider(ImageProvider):
    """Generate PNG assets with the OpenAI Images API.

    Args:
        environ: Environment values. The process environment is the default.
        guard: Optional call guard for controlled tests.
        transport: Optional HTTP transport for controlled tests.
    """

    name = "openai"

    def __init__(
        self,
        *,
        environ: Mapping[str, str] | None = None,
        guard: ApiCallGuard | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        """Read and validate provider settings from the environment."""
        selected_environ = os.environ if environ is None else environ
        api_key = selected_environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            msg = "OPENAI_API_KEY is required when the OpenAI provider is selected."
            raise ProviderConfigurationError(msg)

        model = selected_environ.get("EMOJIBENCH_OPENAI_MODEL", DEFAULT_MODEL).strip()
        if model not in SUPPORTED_MODELS:
            msg = f"EMOJIBENCH_OPENAI_MODEL is not supported: {model!r}."
            raise ProviderConfigurationError(msg)
        size = selected_environ.get("EMOJIBENCH_OPENAI_SIZE", "1024x1024").strip()
        if size not in SUPPORTED_SIZES:
            msg = f"EMOJIBENCH_OPENAI_SIZE is not supported: {size!r}."
            raise ProviderConfigurationError(msg)
        quality = selected_environ.get("EMOJIBENCH_OPENAI_QUALITY", "low").strip()
        if quality not in SUPPORTED_QUALITIES:
            msg = f"EMOJIBENCH_OPENAI_QUALITY is not supported: {quality!r}."
            raise ProviderConfigurationError(msg)

        self.model = model
        self._api_key = api_key
        self._size = size
        self._quality = quality
        self._timeout = _timeout_setting(selected_environ)
        self._retries = _integer_setting(
            selected_environ,
            "EMOJIBENCH_API_RETRIES",
            DEFAULT_RETRIES,
            MAX_RETRIES,
        )
        self._guard = guard or _default_process_guard(selected_environ)
        self._transport = transport

    def generate(self, first: str, second: str) -> GeneratedAsset:
        """Generate one PNG from two catalog concepts.

        Args:
            first: First catalog asset identifier.
            second: Second catalog asset identifier.

        Returns:
            A generated PNG and its draft asset record.

        Raises:
            CostLimitError: If the paid-call limit is reached.
            ProviderError: If validation or the API request fails.
        """
        first_id, second_id = validate_inputs(first, second)
        prompt = creative_brief(first_id, second_id)
        image_bytes = self._request_image(prompt)
        return build_generated_asset(
            first=first_id,
            second=second_id,
            provider=self.name,
            model=self.model,
            settings={
                "format": "png",
                "quality": self._quality,
                "size": self._size,
            },
            prompt=prompt,
            image_bytes=image_bytes,
            source=f"OpenAI Images API ({self.model})",
            license_name="review-required",
            rights_status=(
                "Generated with OpenAI. A human reviewer must confirm publication rights."
            ),
        )

    def _request_image(self, prompt: str) -> bytes:
        """Send a bounded request sequence and decode the PNG response."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "n": 1,
            "size": self._size,
            "quality": self._quality,
            "output_format": "png",
            "background": "opaque",
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        response: httpx.Response | None = None
        for attempt in range(self._retries + 1):
            self._guard.consume()
            try:
                with httpx.Client(
                    timeout=self._timeout,
                    transport=self._transport,
                ) as client:
                    response = client.post(
                        OPENAI_IMAGES_URL,
                        headers=headers,
                        json=payload,
                    )
            except httpx.TimeoutException as error:
                if attempt < self._retries:
                    continue
                msg = f"The OpenAI Images API request timed out: {error}"
                raise ProviderError(msg) from error
            except httpx.RequestError as error:
                if attempt < self._retries:
                    continue
                msg = f"The OpenAI Images API request failed: {error}"
                raise ProviderError(msg) from error

            if response.is_success:
                return self._decode_image(response)
            if response.status_code in {408, 429} or response.status_code >= 500:
                if attempt < self._retries:
                    continue
            cause = self._error_cause(response)
            msg = f"The OpenAI Images API returned HTTP {response.status_code}: {cause}"
            raise ProviderError(msg)

        msg = "The OpenAI Images API request did not produce a response."
        raise ProviderError(msg)

    @staticmethod
    def _error_cause(response: httpx.Response) -> str:
        """Extract a readable cause from an API error response."""
        try:
            data = response.json()
        except ValueError:
            return response.text.strip() or "No error details were returned."
        if isinstance(data, dict):
            error = data.get("error")
            if isinstance(error, dict) and isinstance(error.get("message"), str):
                return error["message"]
        return "No error details were returned."

    @staticmethod
    def _decode_image(response: httpx.Response) -> bytes:
        """Decode the first base64 PNG in a successful API response."""
        try:
            data = response.json()
            encoded = data["data"][0]["b64_json"]
            if not isinstance(encoded, str):
                raise TypeError
            image_bytes = base64.b64decode(encoded, validate=True)
        except (KeyError, IndexError, TypeError, ValueError, binascii.Error) as error:
            msg = "The OpenAI Images API response did not contain a valid image."
            raise ProviderError(msg) from error
        if not image_bytes.startswith(PNG_SIGNATURE):
            msg = "The OpenAI Images API response was not a PNG image."
            raise ProviderError(msg)
        return image_bytes
