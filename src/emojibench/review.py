"""Guarded human review for generated assets."""

from datetime import UTC, datetime
from pathlib import Path

from emojibench.generation import AssetStore
from emojibench.models import Asset, ReviewStatus


class ReviewError(ValueError):
    """A requested review action is absent or not permitted."""


def list_drafts(store_root: str | Path = ".emojibench") -> list[Asset]:
    """Return generated draft assets ordered by identifier.

    Args:
        store_root: Local generation store directory.

    Returns:
        Generated assets that await human review.
    """
    return [asset for asset in AssetStore(store_root).list() if asset.status == "draft"]


def approve_asset(
    asset_id: str,
    *,
    reviewer: str,
    store_root: str | Path = ".emojibench",
) -> Asset:
    """Approve one draft after an explicit human review.

    Args:
        asset_id: Generated draft asset identifier.
        reviewer: Human reviewer name.
        store_root: Local generation store directory.

    Returns:
        The approved asset record.

    Raises:
        ReviewError: If the reviewer is absent or the transition is invalid.
        ValueError: If the asset identifier is unknown.
    """
    return _review_asset(
        asset_id,
        reviewer=reviewer,
        target_status="approved",
        reason=None,
        store_root=store_root,
    )


def reject_asset(
    asset_id: str,
    *,
    reviewer: str,
    reason: str,
    store_root: str | Path = ".emojibench",
) -> Asset:
    """Reject one draft after an explicit human review.

    Args:
        asset_id: Generated draft asset identifier.
        reviewer: Human reviewer name.
        reason: Required rejection reason.
        store_root: Local generation store directory.

    Returns:
        The rejected asset record.

    Raises:
        ReviewError: If review data is absent or the transition is invalid.
        ValueError: If the asset identifier is unknown.
    """
    return _review_asset(
        asset_id,
        reviewer=reviewer,
        target_status="rejected",
        reason=reason,
        store_root=store_root,
    )


def _review_asset(
    asset_id: str,
    *,
    reviewer: str,
    target_status: ReviewStatus,
    reason: str | None,
    store_root: str | Path,
) -> Asset:
    """Apply one permitted draft review transition."""
    selected_reviewer = reviewer.strip()
    if not selected_reviewer:
        msg = "Reviewer name is required."
        raise ReviewError(msg)
    selected_reason = reason.strip() if reason is not None else None
    if target_status == "rejected" and not selected_reason:
        msg = "Rejection reason is required."
        raise ReviewError(msg)

    store = AssetStore(store_root)
    asset = store.get(asset_id)
    if asset.status != "draft":
        msg = (
            f"Asset '{asset_id}' cannot move from {asset.status} "
            f"to {target_status}."
        )
        raise ReviewError(msg)

    review = {
        "reviewer": selected_reviewer,
        "reviewed_at": datetime.now(UTC).isoformat(),
        "decision": target_status,
    }
    if selected_reason is not None:
        review["reason"] = selected_reason
    metadata = dict(asset.generation_metadata or {})
    metadata["review_state"] = target_status
    metadata["review"] = review
    updated = Asset.model_validate(
        {
            **asset.model_dump(),
            "status": target_status,
            "generation_metadata": metadata,
        }
    )
    store.update(updated)
    return updated
