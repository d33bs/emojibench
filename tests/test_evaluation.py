"""Tests for deterministic generated-asset evaluation."""

import hashlib
from pathlib import Path

from emojibench.evaluation import evaluate_asset
from emojibench.generation import AssetStore, GenerationService
from emojibench.models import Asset
from emojibench.providers import GeneratedAsset, MockProvider


def _generate_mock(store_root: Path) -> tuple[str, Path]:
    """Generate and store one mock asset for an evaluation test."""
    with GenerationService(store_root=store_root) as service:
        job = service.submit("macrophage", "superhero", MockProvider())
        finished = service.wait(job.id, timeout=5)
    assert finished.asset_id is not None
    asset = AssetStore(store_root).get(finished.asset_id)
    return asset.id, store_root / asset.image_uri


def test_evaluation_passes_and_never_approves(tmp_path: Path) -> None:
    """A passing deterministic evaluation leaves the asset as a draft."""
    store_root = tmp_path / ".emojibench"
    asset_id, image_path = _generate_mock(store_root)

    result = evaluate_asset(image_path, store_root=store_root)

    assert result.passed
    assert all(item.passed for item in result.checks)
    stored = AssetStore(store_root).get(asset_id)
    assert stored.status == "draft"
    assert stored.generation_metadata is not None
    assert stored.generation_metadata["review_state"] == "draft"
    assert stored.generation_metadata["evaluation"]["passed"] is True


def test_evaluation_detects_checksum_change(tmp_path: Path) -> None:
    """A changed image fails checksum and decode checks."""
    store_root = tmp_path / ".emojibench"
    _asset_id, image_path = _generate_mock(store_root)
    image_path.write_bytes(image_path.read_bytes() + b"changed")

    result = evaluate_asset(image_path, store_root=store_root)

    assert not result.passed
    checks = {item.name: item for item in result.checks}
    assert not checks["content_checksum"].passed


def test_evaluation_decodes_svg_with_expected_dimensions(tmp_path: Path) -> None:
    """The evaluator parses a valid generated SVG and its dimensions."""
    store_root = tmp_path / ".emojibench"
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="20" height="10"/>'
    checksum = f"sha256:{hashlib.sha256(svg).hexdigest()}"
    asset = Asset(
        id="generated-svg-sample",
        name="Generated SVG sample",
        category="generated",
        tags=["sample"],
        image_uri="generated/generated-svg-sample.svg",
        source="Test provider",
        license="BSD-3-Clause",
        kind="generated",
        status="draft",
        generation_metadata={
            "inputs": ["macrophage", "superhero"],
            "creative_brief": "Test SVG.",
            "prompt": "Test SVG.",
            "provider": "mock",
            "model": "mock",
            "settings": {"format": "svg", "size": "20x10"},
            "generated_at": "2026-01-02T00:00:00+00:00",
            "output_checksum": checksum,
            "rights_status": "Original test asset.",
            "license": "BSD-3-Clause",
            "review_state": "draft",
        },
    )
    AssetStore(store_root).save(GeneratedAsset(asset=asset, image_bytes=svg))

    result = evaluate_asset(store_root / asset.image_uri, store_root=store_root)

    assert result.passed


def test_evaluation_requires_metadata(tmp_path: Path) -> None:
    """An image without generated-asset metadata fails evaluation."""
    image_path = tmp_path / "orphan.png"
    image_path.write_bytes(b"not an image")

    result = evaluate_asset(image_path)

    assert not result.passed
    checks = {item.name: item for item in result.checks}
    assert not checks["metadata_present"].passed
