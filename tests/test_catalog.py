"""Tests for the offline asset catalog."""

import json
from pathlib import Path

import pytest

from emojibench.catalog import CatalogError, load_catalog, resolve_asset_path

MIN_CATALOG_SIZE = 6
MAX_CATALOG_SIZE = 10


def test_bundled_catalog_loads_original_assets() -> None:
    """The bundled catalog contains valid local original artwork."""
    assets = load_catalog()
    assets_by_id = {asset.id: asset for asset in assets}

    assert MIN_CATALOG_SIZE <= len(assets) <= MAX_CATALOG_SIZE
    assert {"macrophage", "superhero"} <= assets_by_id.keys()
    assert all(asset.kind == "original" for asset in assets)
    assert all(asset.license == "BSD-3-Clause" for asset in assets)
    assert all(resolve_asset_path(asset).is_file() for asset in assets)


def test_catalog_reports_malformed_json(tmp_path: Path) -> None:
    """The loader reports a clear error for invalid JSON syntax."""
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(CatalogError, match="Catalog JSON is malformed"):
        load_catalog(catalog_path)


def test_catalog_reports_invalid_asset_data(tmp_path: Path) -> None:
    """The loader reports a clear error for an invalid asset record."""
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "assets": [
                    {
                        "id": "bad id",
                        "name": "Broken",
                        "category": "test",
                        "tags": [],
                        "image_uri": "assets/broken.svg",
                        "source": "Test",
                        "license": "BSD-3-Clause",
                        "kind": "original",
                        "status": "draft",
                        "schema_version": "1.0",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(CatalogError, match="Catalog data is invalid"):
        load_catalog(catalog_path)


def test_catalog_reports_duplicate_ids(tmp_path: Path) -> None:
    """The loader rejects duplicate asset identifiers."""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "sample.svg").write_text("<svg/>", encoding="utf-8")
    asset = {
        "id": "sample",
        "name": "Sample",
        "category": "test",
        "tags": [],
        "image_uri": "assets/sample.svg",
        "source": "Test",
        "license": "BSD-3-Clause",
        "kind": "original",
        "status": "draft",
        "schema_version": "1.0",
    }
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(
        json.dumps({"schema_version": "1.0", "assets": [asset, asset]}),
        encoding="utf-8",
    )

    with pytest.raises(CatalogError, match="duplicate asset id: sample"):
        load_catalog(catalog_path)


def test_catalog_reports_missing_image(tmp_path: Path) -> None:
    """The loader rejects an asset when its local image is absent."""
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "assets": [
                    {
                        "id": "sample",
                        "name": "Sample",
                        "category": "test",
                        "tags": [],
                        "image_uri": "assets/missing.svg",
                        "source": "Test",
                        "license": "BSD-3-Clause",
                        "kind": "original",
                        "status": "draft",
                        "schema_version": "1.0",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(CatalogError, match="Catalog image does not exist"):
        load_catalog(catalog_path)
