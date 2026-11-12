"""Tests for human review and public catalog filtering."""

from pathlib import Path

import pytest

from emojibench.catalog import public_catalog
from emojibench.generation import AssetStore, GenerationService
from emojibench.providers import MockProvider
from emojibench.review import ReviewError, approve_asset, list_drafts, reject_asset


def _draft_asset(store_root: Path) -> str:
    """Create one stored draft and return its identifier."""
    with GenerationService(store_root=store_root) as service:
        job = service.submit("macrophage", "superhero", MockProvider())
        finished = service.wait(job.id, timeout=5)
    assert finished.asset_id is not None
    return finished.asset_id


def test_approve_requires_reviewer_and_publishes_asset(tmp_path: Path) -> None:
    """Only an explicit human review moves a draft into the public view."""
    store_root = tmp_path / ".emojibench"
    asset_id = _draft_asset(store_root)

    assert asset_id in {asset.id for asset in list_drafts(store_root)}
    assert asset_id not in {asset.id for asset in public_catalog(store_root)}
    with pytest.raises(ReviewError, match="Reviewer name is required"):
        approve_asset(asset_id, reviewer=" ", store_root=store_root)

    approved = approve_asset(asset_id, reviewer="Ada Reviewer", store_root=store_root)

    assert approved.status == "approved"
    assert approved.generation_metadata is not None
    assert approved.generation_metadata["review"]["reviewer"] == "Ada Reviewer"
    assert asset_id in {asset.id for asset in public_catalog(store_root)}


def test_approve_transition_is_enforced(tmp_path: Path) -> None:
    """An approved asset cannot receive a second approval."""
    store_root = tmp_path / ".emojibench"
    asset_id = _draft_asset(store_root)
    approve_asset(asset_id, reviewer="First Reviewer", store_root=store_root)

    with pytest.raises(ReviewError, match="cannot move from approved to approved"):
        approve_asset(asset_id, reviewer="Second Reviewer", store_root=store_root)


def test_rejected_asset_cannot_be_approved_or_published(tmp_path: Path) -> None:
    """A rejection is terminal and excludes the asset from public results."""
    store_root = tmp_path / ".emojibench"
    asset_id = _draft_asset(store_root)

    rejected = reject_asset(
        asset_id,
        reviewer="Ada Reviewer",
        reason="The concepts are not recognizable.",
        store_root=store_root,
    )

    assert rejected.status == "rejected"
    assert asset_id not in {asset.id for asset in public_catalog(store_root)}
    with pytest.raises(ReviewError, match="cannot move from rejected to approved"):
        approve_asset(asset_id, reviewer="Another Reviewer", store_root=store_root)


def test_reject_requires_reviewer_reason_and_valid_id(tmp_path: Path) -> None:
    """Rejection needs a reviewer, a reason, and a stored asset."""
    store_root = tmp_path / ".emojibench"
    asset_id = _draft_asset(store_root)

    with pytest.raises(ReviewError, match="Reviewer name is required"):
        reject_asset(asset_id, reviewer="", reason="No.", store_root=store_root)
    with pytest.raises(ReviewError, match="Rejection reason is required"):
        reject_asset(asset_id, reviewer="Ada", reason="", store_root=store_root)
    with pytest.raises(ValueError, match="Unknown generated asset id 'missing'"):
        approve_asset("missing", reviewer="Ada", store_root=store_root)


def test_generated_store_keeps_review_update(tmp_path: Path) -> None:
    """Review changes remain in the central store and sidecar metadata."""
    store_root = tmp_path / ".emojibench"
    asset_id = _draft_asset(store_root)

    approve_asset(asset_id, reviewer="Ada Reviewer", store_root=store_root)

    stored = AssetStore(store_root).get(asset_id)
    sidecar = store_root / stored.image_uri
    sidecar_asset = AssetStore(store_root).load_sidecar(sidecar.with_suffix(".json"))
    assert stored == sidecar_asset
