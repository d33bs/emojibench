"""Tests for the emojibench data models."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from emojibench.models import Asset, Combination, Story


def asset_data() -> dict[str, object]:
    """Return valid data for one original asset."""
    return {
        "id": "macrophage",
        "name": "Macrophage",
        "category": "cells",
        "tags": ["cell", "immune"],
        "image_uri": "assets/macrophage.svg",
        "source": "Emojibench original artwork",
        "license": "BSD-3-Clause",
        "kind": "original",
        "status": "approved",
        "schema_version": "1.0",
    }


def test_asset_accepts_valid_data_and_round_trips() -> None:
    """An asset keeps its data through JSON serialization."""
    asset = Asset.model_validate(asset_data())

    restored = Asset.model_validate_json(asset.model_dump_json())

    assert restored == asset
    assert restored.id == "macrophage"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", "Not a slug"),
        ("name", ""),
        ("kind", "copied"),
        ("status", "published"),
        ("image_uri", "https://example.com/image.svg"),
    ],
)
def test_asset_rejects_invalid_data(field: str, value: object) -> None:
    """An asset rejects invalid identifiers, values, and remote images."""
    data = asset_data()
    data[field] = value

    with pytest.raises(ValidationError):
        Asset.model_validate(data)


def test_asset_rejects_extra_fields() -> None:
    """An asset rejects fields that are not part of the schema."""
    data = asset_data()
    data["unknown"] = True

    with pytest.raises(ValidationError):
        Asset.model_validate(data)


def test_combination_normalizes_input_order_and_round_trips() -> None:
    """A combination stores the input identifiers in canonical order."""
    combination = Combination(
        id="combination-abc123",
        input_ids=("superhero", "macrophage"),
        status="draft",
        created_at=datetime(2026, 1, 2, tzinfo=UTC),
    )

    restored = Combination.model_validate_json(combination.model_dump_json())

    assert combination.input_ids == ("macrophage", "superhero")
    assert restored == combination


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("input_ids", ("macrophage",)),
        ("input_ids", ("bad id", "superhero")),
        ("status", "complete"),
        ("created_at", datetime(2026, 1, 2)),
    ],
)
def test_combination_rejects_invalid_data(field: str, value: object) -> None:
    """A combination rejects invalid pairs, states, and timestamps."""
    data: dict[str, object] = {
        "id": "combination-abc123",
        "input_ids": ("macrophage", "superhero"),
        "status": "draft",
        "created_at": datetime(2026, 1, 2, tzinfo=UTC),
    }
    data[field] = value

    with pytest.raises(ValidationError):
        Combination.model_validate(data)


def test_story_accepts_ordered_panels_and_round_trips() -> None:
    """A story keeps panel order and optional references."""
    story = Story(
        id="cell-rescue",
        title="Cell Rescue",
        audience="kids",
        panels=[
            {
                "asset_id": "macrophage",
                "caption": "A macrophage approaches.",
                "references": ["asset:macrophage"],
                "evidence_status": "observation",
            },
            {
                "asset_id": "superhero",
                "caption": "The rescue theme is a playful analogy.",
                "evidence_status": "creative_analogy",
            },
        ],
        status="draft",
        created_at=datetime(2026, 1, 2, tzinfo=UTC),
    )

    restored = Story.model_validate_json(story.model_dump_json())

    assert [panel.asset_id for panel in restored.panels] == [
        "macrophage",
        "superhero",
    ]
    assert restored == story


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", "bad id"),
        ("title", ""),
        ("panels", []),
        ("status", "ready"),
        ("created_at", datetime(2026, 1, 2)),
    ],
)
def test_story_rejects_invalid_data(field: str, value: object) -> None:
    """A story rejects invalid identifiers, content, and timestamps."""
    data: dict[str, object] = {
        "id": "cell-rescue",
        "title": "Cell Rescue",
        "audience": "kids",
        "panels": [
            {
                "asset_id": "macrophage",
                "caption": "A macrophage approaches.",
                "evidence_status": "observation",
            }
        ],
        "status": "draft",
        "created_at": datetime(2026, 1, 2, tzinfo=UTC),
    }
    data[field] = value

    with pytest.raises(ValidationError):
        Story.model_validate(data)


def test_story_rejects_invalid_panel_evidence_status() -> None:
    """A story panel accepts only defined evidence states."""
    data: dict[str, object] = {
        "id": "cell-rescue",
        "title": "Cell Rescue",
        "audience": "kids",
        "panels": [
            {
                "asset_id": "macrophage",
                "caption": "A macrophage approaches.",
                "evidence_status": "fact",
            }
        ],
        "status": "draft",
        "created_at": datetime(2026, 1, 2, tzinfo=UTC),
    }

    with pytest.raises(ValidationError):
        Story.model_validate(data)
