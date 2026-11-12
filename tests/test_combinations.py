"""Tests for deterministic offline combinations."""

import json
import struct
from pathlib import Path

import pytest

from emojibench.catalog import CatalogError
from emojibench.combinations import (
    combination_id,
    create_combination,
    record_combination,
    write_preview,
)

PNG_IHDR_LENGTH = 13


def test_combination_id_is_stable_for_normalized_pair() -> None:
    """Input order does not change the stable combination identifier."""
    forward = combination_id("macrophage", "superhero")
    reverse = combination_id("superhero", "macrophage")

    assert forward == reverse
    assert forward.startswith("combination-")
    assert len(forward) == len("combination-") + 16


def test_svg_preview_is_deterministic_and_contains_both_assets(
    tmp_path: Path,
) -> None:
    """The SVG preview is byte-identical for either input order."""
    forward_path = tmp_path / "forward.svg"
    reverse_path = tmp_path / "reverse.svg"

    write_preview("macrophage", "superhero", forward_path)
    write_preview("superhero", "macrophage", reverse_path)

    forward = forward_path.read_bytes()
    assert forward == reverse_path.read_bytes()
    assert b"macrophage" in forward
    assert b"superhero" in forward
    assert b"Mock offline preview" in forward


def test_png_preview_is_a_decodable_truecolor_image(tmp_path: Path) -> None:
    """The PNG preview has a valid signature and image header."""
    output_path = tmp_path / "preview.png"

    write_preview("macrophage", "superhero", output_path)

    data = output_path.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    ihdr_length = struct.unpack(">I", data[8:12])[0]
    assert data[12:16] == b"IHDR"
    width, height = struct.unpack(">II", data[16:24])
    assert ihdr_length == PNG_IHDR_LENGTH
    assert (width, height) == (512, 320)
    assert data.endswith(b"IEND\xaeB`\x82")


def test_preview_rejects_unknown_assets(tmp_path: Path) -> None:
    """The preview reports an unknown source identifier."""
    with pytest.raises(CatalogError, match="Unknown asset id 'missing'"):
        write_preview("missing", "superhero", tmp_path / "preview.svg")


def test_preview_rejects_unknown_file_type(tmp_path: Path) -> None:
    """The preview accepts only SVG and PNG output files."""
    with pytest.raises(ValueError, match="Output file must use .svg or .png"):
        write_preview("macrophage", "superhero", tmp_path / "preview.jpg")


def test_combination_record_is_created_and_updated(tmp_path: Path) -> None:
    """The JSON store keeps one record for a stable input pair."""
    store_path = tmp_path / ".emojibench" / "combinations.json"
    first = create_combination("macrophage", "superhero")
    second = create_combination("superhero", "macrophage")

    record_combination(first, store_path)
    record_combination(second, store_path)

    data = json.loads(store_path.read_text(encoding="utf-8"))
    assert data["schema_version"] == "1.0"
    assert len(data["combinations"]) == 1
    assert data["combinations"][0]["id"] == first.id
    assert data["combinations"][0]["input_ids"] == [
        "macrophage",
        "superhero",
    ]
