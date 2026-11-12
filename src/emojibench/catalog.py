"""Load and validate the bundled offline asset catalog."""

import json
from pathlib import Path

from pydantic import Field, ValidationError

from emojibench.models import Asset, NonEmptyString, StrictModel

DEFAULT_CATALOG_PATH = Path(__file__).parent / "data" / "catalog.json"


class CatalogError(ValueError):
    """An error in a catalog file or one of its asset records."""


class CatalogDocument(StrictModel):
    """The on-disk catalog document.

    Attributes:
        schema_version: Version of the catalog document schema.
        assets: Validated asset records in display order.
    """

    schema_version: NonEmptyString
    assets: list[Asset] = Field(min_length=1)


def catalog_path(path: str | Path | None = None) -> Path:
    """Return the selected catalog path.

    Args:
        path: Optional path that replaces the bundled catalog.

    Returns:
        The absolute or relative catalog path.
    """
    return Path(path) if path is not None else DEFAULT_CATALOG_PATH


def resolve_asset_path(
    asset: Asset,
    source_catalog_path: str | Path | None = None,
) -> Path:
    """Resolve an asset image relative to its catalog.

    Args:
        asset: Asset with a validated local image path.
        source_catalog_path: Catalog that contains the asset record.

    Returns:
        The resolved local image path.
    """
    return catalog_path(source_catalog_path).parent / asset.image_uri


def load_catalog(path: str | Path | None = None) -> list[Asset]:
    """Load a catalog and validate its records and local images.

    Args:
        path: Optional path that replaces the bundled catalog.

    Returns:
        Assets in catalog display order.

    Raises:
        CatalogError: If the file, JSON, records, or image paths are invalid.
    """
    selected_path = catalog_path(path)
    try:
        raw_text = selected_path.read_text(encoding="utf-8")
    except OSError as error:
        msg = f"Catalog file could not be read: {selected_path}: {error}"
        raise CatalogError(msg) from error

    try:
        raw_data = json.loads(raw_text)
    except json.JSONDecodeError as error:
        msg = (
            "Catalog JSON is malformed: "
            f"{selected_path}:{error.lineno}:{error.colno}: {error.msg}"
        )
        raise CatalogError(msg) from error

    try:
        document = CatalogDocument.model_validate(raw_data)
    except ValidationError as error:
        msg = f"Catalog data is invalid: {selected_path}: {error}"
        raise CatalogError(msg) from error

    seen_ids: set[str] = set()
    for asset in document.assets:
        if asset.id in seen_ids:
            msg = f"Catalog contains duplicate asset id: {asset.id}"
            raise CatalogError(msg)
        seen_ids.add(asset.id)

        image_path = resolve_asset_path(asset, selected_path)
        if not image_path.is_file():
            msg = f"Catalog image does not exist: {image_path}"
            raise CatalogError(msg)

    return document.assets


def asset_by_id(asset_id: str, assets: list[Asset] | None = None) -> Asset:
    """Find one catalog asset by identifier.

    Args:
        asset_id: Exact asset slug to find.
        assets: Optional preloaded catalog assets.

    Returns:
        The matching asset.

    Raises:
        CatalogError: If the catalog does not contain the identifier.
    """
    selected_assets = assets if assets is not None else load_catalog()
    for asset in selected_assets:
        if asset.id == asset_id:
            return asset
    available_ids = ", ".join(asset.id for asset in selected_assets)
    msg = f"Unknown asset id '{asset_id}'. Available ids: {available_ids}"
    raise CatalogError(msg)


def public_catalog(store_root: str | Path = ".emojibench") -> list[Asset]:
    """Return approved bundled and generated assets.

    Args:
        store_root: Local generated-asset store directory.

    Returns:
        Approved assets that can appear in a public catalog.
    """
    from emojibench.generation import AssetStore  # Avoid an import cycle.

    bundled = [asset for asset in load_catalog() if asset.status == "approved"]
    generated = [
        asset for asset in AssetStore(store_root).list() if asset.status == "approved"
    ]
    return [*bundled, *generated]
