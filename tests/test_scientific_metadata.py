"""Tests for scientific asset metadata and microscopy source links."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from emojibench.models import Asset, MicroscopySource


def _scientific_asset(**overrides: object) -> dict[str, object]:
    """Build a scientific asset payload with a microscopy source."""
    base: dict[str, object] = {
        "id": "rxrx19a-cell-crop",
        "name": "RxRx19a cell crop",
        "category": "cells",
        "tags": ["microscopy", "rxrx19a"],
        "image_uri": "assets/rxrx19a-cell-crop.svg",
        "source": "RxRx19a reanalysis (WayScience)",
        "license": "CC-BY-4.0",
        "kind": "scientific",
        "status": "draft",
        "scientific_metadata": {
            "microscopy_source": {
                "dataset": "RxRx19a",
                "image_uri": "images/Plate1/WellA1.tif",
                "attribution": "Recursion Pharmaceuticals, CC-BY-4.0",
                "license": "CC-BY-4.0",
                "crop": [32, 48, 64, 64],
                "object_id": 7,
                "dimensions": [520, 696],
                "measurements": {"area": 412.5, "eccentricity": 0.62},
                "references": [
                    "RxRx19a: a phenotypic dataset (Recursion, 2020)."
                ],
            }
        },
    }
    base.update(overrides)
    return base


def test_microscopy_source_validates_full_record() -> None:
    """A complete microscopy source passes and round-trips."""
    payload = _scientific_asset()["scientific_metadata"]
    assert isinstance(payload, dict)
    source = MicroscopySource.model_validate(payload["microscopy_source"])
    assert source.dataset == "RxRx19a"
    assert source.crop == (32, 48, 64, 64)
    assert source.object_id == 7
    assert source.dimensions == (520, 696)
    round_trip = MicroscopySource.model_validate(
        source.model_dump(mode="json")
    )
    assert round_trip == source


def test_scientific_asset_requires_microscopy_source() -> None:
    """A scientific asset without a microscopy source is rejected."""
    with pytest.raises(ValidationError, match="scientific_metadata with a source"):
        Asset.model_validate(_scientific_asset(scientific_metadata=None))

    with pytest.raises(ValidationError, match="microscopy source"):
        Asset.model_validate(
            _scientific_asset(
                scientific_metadata={"microscopy_source": {"dataset": "x"}}
            )
        )


def test_non_scientific_asset_ignores_microscopy_rule() -> None:
    """Original assets stay valid without scientific metadata."""
    payload = _scientific_asset(
        kind="original",
        scientific_metadata=None,
        id="plain-asset",
        image_uri="assets/plain-asset.svg",
    )
    asset = Asset.model_validate(payload)
    assert asset.kind == "original"
    assert asset.scientific_metadata is None


def test_microscopy_source_rejects_unknown_fields() -> None:
    """The microscopy model forbids unknown keys."""
    payload = _scientific_asset()["scientific_metadata"]
    assert isinstance(payload, dict)
    bad = dict(payload["microscopy_source"])
    bad["surprise"] = True
    with pytest.raises(ValidationError):
        MicroscopySource.model_validate(bad)


def test_fixture_example_is_valid(tmp_path: Path) -> None:
    """The bundled metadata-only example validates as an asset."""
    import json

    fixture = (
        Path(__file__).parents[1]
        / "examples"
        / "scientific-metadata-example.json"
    )
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    asset = Asset.model_validate(payload)
    assert asset.kind == "scientific"
    assert asset.scientific_metadata is not None
    source = MicroscopySource.model_validate(
        asset.scientific_metadata["microscopy_source"]
    )
    assert source.dataset == "RxRx19a"
