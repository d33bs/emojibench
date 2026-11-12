"""Tests for story composition and export."""

import json
from pathlib import Path

import pytest

from emojibench.stories import (
    MAX_PANELS,
    MIN_PANELS,
    StoryError,
    compose_story,
    save_story,
    story_slug,
)


def _panel(asset_id: str, caption: str) -> dict[str, object]:
    """Build one plain story panel dictionary."""
    return {
        "asset_id": asset_id,
        "caption": caption,
        "evidence_status": "creative_analogy",
    }


def test_story_slug_converts_titles() -> None:
    """Titles become stable lowercase slugs."""
    assert story_slug("A Macrophage Saves the Day!") == "a-macrophage-saves-the-day"
    assert story_slug("   ") == "story"


def test_compose_story_accepts_approved_assets() -> None:
    """A three-panel story from bundled approved assets is valid."""
    story = compose_story(
        "A Macrophage Saves the Day",
        "kids",
        [
            _panel("macrophage", "Meet the macrophage."),
            _panel("petri-dish", "A germ shows up."),
            _panel("superhero", "The macrophage saves the day."),
        ],
    )

    assert story.id == "a-macrophage-saves-the-day"
    assert story.status == "draft"
    assert len(story.panels) == 3
    assert story.panels[1].asset_id == "petri-dish"
    assert story.audience == "kids"


def test_compose_story_rejects_short_and_long_stories() -> None:
    """Panel count must stay between the minimum and the maximum."""
    with pytest.raises(StoryError, match="3 to 5 panels"):
        compose_story("Too short", "kids", [_panel("macrophage", "Hi.")])

    with pytest.raises(StoryError, match="3 to 5 panels"):
        compose_story(
            "Too long",
            "kids",
            [_panel("macrophage", f"Panel {i}.") for i in range(MAX_PANELS + 1)],
        )


def test_compose_story_rejects_unapproved_assets(tmp_path: Path) -> None:
    """A draft generated asset cannot enter a story."""
    store_root = tmp_path / ".emojibench"
    from emojibench.generation import AssetStore, GenerationService
    from emojibench.providers import MockProvider

    with GenerationService(store_root=store_root) as service:
        job = service.submit("macrophage", "superhero", MockProvider())
        finished = service.wait(job.id, timeout=5)
    assert finished.asset_id is not None
    draft_id = finished.asset_id

    with pytest.raises(StoryError, match="not an approved public asset"):
        compose_story(
            "Draft story",
            "kids",
            [
                _panel("macrophage", "One."),
                _panel(draft_id, "Two."),
                _panel("superhero", "Three."),
            ],
            store_root=store_root,
        )


def test_compose_story_accepts_observation_with_references() -> None:
    """Observation panels carry references and keep their evidence status."""
    story = compose_story(
        "Cell story",
        "researchers",
        [
            {
                "asset_id": "macrophage",
                "caption": "The cell in the crop is elongated.",
                "references": ["RxRx19a dataset, plate 1, well A1."],
                "evidence_status": "observation",
            },
            _panel("dna-helix", "The instructions sit in the nucleus."),
            _panel("cell-nucleus", "The nucleus holds them."),
        ],
    )

    assert story.panels[0].evidence_status == "observation"
    assert story.panels[0].references == ["RxRx19a dataset, plate 1, well A1."]


def test_save_story_exports_json_and_panels(tmp_path: Path) -> None:
    """Export writes story JSON and copies each panel image."""
    story = compose_story(
        "A Macrophage Saves the Day",
        "kids",
        [
            _panel("macrophage", "Meet the macrophage."),
            _panel("petri-dish", "A germ shows up."),
            _panel("superhero", "The macrophage saves the day."),
        ],
    )

    output_dir = tmp_path / "export"
    json_path = save_story(story, output_dir)

    assert json_path.is_file()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["id"] == "a-macrophage-saves-the-day"
    assert len(data["panels"]) == 3
    panels_written = sorted(
        p.name for p in output_dir.glob("panel-*") if p.suffix == ".svg"
    )
    assert len(panels_written) == 3


def test_save_story_rejects_unknown_asset(tmp_path: Path) -> None:
    """Export fails clearly when a panel asset is missing."""
    story = compose_story(
        "A Macrophage Saves the Day",
        "kids",
        [
            _panel("macrophage", "One."),
            _panel("petri-dish", "Two."),
            _panel("superhero", "Three."),
        ],
    )
    # Simulate a vanished asset by pointing the first panel at a bad id.
    story.panels[0].asset_id = "missing-asset"

    with pytest.raises(StoryError, match="unknown asset"):
        save_story(story, tmp_path / "export")
