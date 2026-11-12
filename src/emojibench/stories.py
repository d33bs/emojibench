"""Story composition from approved public assets."""

from datetime import UTC, datetime
from pathlib import Path

from emojibench.catalog import public_catalog
from emojibench.models import Asset, Story, StoryPanel


class StoryError(ValueError):
    """A requested story action is invalid."""


MIN_PANELS = 3
MAX_PANELS = 5


def public_asset_ids(store_root: str | Path = ".emojibench") -> set[str]:
    """Return identifiers of all approved public assets.

    Args:
        store_root: Local generated-asset store directory.

    Returns:
        Asset identifiers eligible for story panels.
    """
    return {asset.id for asset in public_catalog(store_root)}


def compose_story(
    title: str,
    audience: str,
    panels: list[dict[str, object]],
    *,
    store_root: str | Path = ".emojibench",
) -> Story:
    """Build one story from approved assets and plain panel data.

    Args:
        title: Human-readable story title.
        audience: Intended reader group, for example "kids".
        panels: Ordered panel dictionaries with keys asset_id, caption,
            optional references, and evidence_status.
        store_root: Local generated-asset store directory.

    Returns:
        The validated story.

    Raises:
        StoryError: If the panel count, assets, or panel data are invalid.
    """
    if not MIN_PANELS <= len(panels) <= MAX_PANELS:
        msg = (
            f"A story needs {MIN_PANELS} to {MAX_PANELS} panels; "
            f"got {len(panels)}."
        )
        raise StoryError(msg)

    approved_ids = public_asset_ids(store_root)
    for panel in panels:
        asset_id = panel.get("asset_id")
        if asset_id not in approved_ids:
            msg = (
                f"Panel asset '{asset_id}' is not an approved public asset. "
                "Only approved assets can enter a story."
            )
            raise StoryError(msg)

    parsed = [StoryPanel.model_validate(panel) for panel in panels]
    story_id = story_slug(title)
    return Story(
        id=story_id,
        title=title,
        audience=audience,
        panels=parsed,
        status="draft",
        created_at=datetime.now(UTC),
    )


def story_slug(title: str) -> str:
    """Convert a story title into a stable slug identifier.

    Args:
        title: Human-readable story title.

    Returns:
        A lowercase slug with words joined by single hyphens.
    """
    words = "".join(
        character if character.isalnum() else " " for character in title.lower()
    ).split()
    return "-".join(words) if words else "story"


def save_story(
    story: Story,
    output_dir: str | Path,
) -> Path:
    """Write one story as JSON plus its panel images.

    Args:
        story: Story to export.
        output_dir: Destination directory for the story bundle.

    Returns:
        The path of the written story JSON file.

    Raises:
        StoryError: If a panel image cannot be found or copied.
    """
    from shutil import copy2

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    assets_by_id = {asset.id: asset for asset in public_catalog()}
    for index, panel in enumerate(story.panels, start=1):
        asset = assets_by_id.get(panel.asset_id)
        if asset is None:
            msg = f"Panel {index} references unknown asset '{panel.asset_id}'."
            raise StoryError(msg)
        source = resolve_asset_image(asset)
        suffix = source.suffix
        target = destination / f"panel-{index:02d}{suffix}"
        copy2(source, target)
    json_path = destination / f"{story.id}.json"
    json_path.write_text(
        story.model_dump_json(indent=2), encoding="utf-8"
    )
    return json_path


def resolve_asset_image(asset: Asset) -> Path:
    """Return the local image path for one catalog asset.

    Args:
        asset: Catalog asset with a bundled image URI.

    Returns:
        Path of the asset image file.

    Raises:
        StoryError: If the image file does not exist.
    """
    from emojibench.catalog import resolve_asset_path

    path = resolve_asset_path(asset)
    if not path.is_file():
        msg = f"Asset image is missing: {path}"
        raise StoryError(msg)
    return path
