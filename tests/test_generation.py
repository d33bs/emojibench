"""Tests for local generation jobs and asset storage."""

import json
from pathlib import Path

from emojibench.generation import AssetStore, GenerationService
from emojibench.providers import MockProvider


def test_generation_job_succeeds_and_persists_asset(tmp_path: Path) -> None:
    """A worker records state changes and writes the image and metadata."""
    store_root = tmp_path / ".emojibench"

    with GenerationService(store_root=store_root) as service:
        submitted = service.submit("macrophage", "superhero", MockProvider())
        finished = service.wait(submitted.id, timeout=5)

    assert submitted.state == "queued"
    assert finished.state == "succeeded"
    assert finished.asset_id is not None
    asset = AssetStore(store_root).get(finished.asset_id)
    image_path = store_root / asset.image_uri
    assert image_path.is_file()
    assert image_path.with_suffix(".json").is_file()

    jobs = json.loads((store_root / "jobs.json").read_text(encoding="utf-8"))
    assert jobs["jobs"][0]["state"] == "succeeded"
    assert jobs["jobs"][0]["error"] is None


def test_generation_job_failure_keeps_the_cause(tmp_path: Path) -> None:
    """A provider error becomes a failed job with a readable cause."""
    store_root = tmp_path / ".emojibench"

    with GenerationService(store_root=store_root) as service:
        submitted = service.submit("missing", "superhero", MockProvider())
        finished = service.wait(submitted.id, timeout=5)

    assert finished.state == "failed"
    assert finished.error is not None
    assert "Unknown asset id 'missing'" in finished.error


def test_asset_store_rejects_unknown_id(tmp_path: Path) -> None:
    """The local store reports an invalid generated asset identifier."""
    store = AssetStore(tmp_path / ".emojibench")

    try:
        store.get("missing")
    except ValueError as error:
        assert str(error) == "Unknown generated asset id 'missing'."
    else:
        raise AssertionError("The store accepted an unknown asset id")
