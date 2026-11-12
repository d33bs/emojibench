"""Create deterministic mock previews without network access."""

import base64
import hashlib
import html
import struct
import zlib
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from emojibench.catalog import (
    asset_by_id,
    load_catalog,
    resolve_asset_path,
)
from emojibench.models import Combination, NonEmptyString, StrictModel

PREVIEW_WIDTH = 512
PREVIEW_HEIGHT = 320

_FONT: dict[str, tuple[str, ...]] = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "J": ("00111", "00010", "00010", "00010", "10010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
}


class CombinationStoreError(ValueError):
    """An error in the local combination store."""


class CombinationStore(StrictModel):
    """The local JSON record of created combinations.

    Attributes:
        schema_version: Version of the store schema.
        combinations: Saved combinations ordered by identifier.
    """

    schema_version: NonEmptyString = "1.0"
    combinations: list[Combination]


def normalize_pair(first: str, second: str) -> tuple[str, str]:
    """Return two identifiers in canonical order.

    Args:
        first: First asset identifier.
        second: Second asset identifier.

    Returns:
        The normalized pair.
    """
    return (first, second) if first <= second else (second, first)


def combination_id(first: str, second: str) -> str:
    """Derive a stable identifier from two asset identifiers.

    Args:
        first: First asset identifier.
        second: Second asset identifier.

    Returns:
        A slug with a stable SHA-256 prefix.
    """
    normalized = normalize_pair(first, second)
    digest = hashlib.sha256("\0".join(normalized).encode()).hexdigest()[:16]
    return f"combination-{digest}"


def create_combination(first: str, second: str) -> Combination:
    """Create a draft record for two catalog assets.

    Args:
        first: First catalog asset identifier.
        second: Second catalog asset identifier.

    Returns:
        A validated draft combination.

    Raises:
        CatalogError: If either identifier is absent from the catalog.
    """
    assets = load_catalog()
    asset_by_id(first, assets)
    asset_by_id(second, assets)
    return Combination(
        id=combination_id(first, second),
        input_ids=(first, second),
        status="draft",
        created_at=datetime.now(UTC),
        evaluation={
            "preview_type": "mock",
            "provider": "mock",
            "rights_status": "original inputs under the BSD-3-Clause license",
            "review_state": "draft",
        },
    )


def _svg_data_uri(asset_id: str) -> str:
    """Return a bundled asset as an SVG data URI."""
    asset = asset_by_id(asset_id)
    image_bytes = resolve_asset_path(asset).read_bytes()
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def _render_svg(first_id: str, second_id: str) -> bytes:
    """Build a side-by-side SVG from two bundled source images."""
    first = asset_by_id(first_id)
    second = asset_by_id(second_id)
    title = html.escape(f"Mock offline preview: {first.name} + {second.name}")
    first_uri = _svg_data_uri(first.id)
    second_uri = _svg_data_uri(second.id)
    first_label = html.escape(first.id)
    second_label = html.escape(second.id)
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg"\n'
        '  width="512" height="320" viewBox="0 0 512 320"\n'
        '  role="img" aria-labelledby="title">\n'
        f'  <title id="title">{title}</title>\n'
        "  <metadata>Mock offline preview. Original emojibench inputs. "
        "BSD-3-Clause license.</metadata>\n"
        '  <rect width="512" height="320" rx="32" fill="#fffaf2"/>\n'
        '  <circle cx="244" cy="146" r="72" fill="#ffe8a3"\n'
        '    opacity="0.7"/>\n'
        f'  <image href="{first_uri}" x="48" y="48"\n'
        '    width="200" height="200"/>\n'
        f'  <image href="{second_uri}" x="264" y="48"\n'
        '    width="200" height="200"/>\n'
        '  <path d="M246 130h20M256 120v20" stroke="#263238"\n'
        '    stroke-width="8" stroke-linecap="round"/>\n'
        '  <text x="256" y="286" text-anchor="middle"\n'
        '    font-family="system-ui, sans-serif" font-size="20" fill="#263238">'
        f"Mock offline preview · {first_label} + {second_label}</text>\n"
        "</svg>\n"
    )
    return svg.encode()


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    """Pack one PNG chunk with its checksum."""
    checksum = zlib.crc32(kind + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)


def _set_pixel(
    pixels: bytearray,
    x: int,
    y: int,
    color: tuple[int, int, int],
) -> None:
    """Set one pixel when its coordinates are inside the preview."""
    if 0 <= x < PREVIEW_WIDTH and 0 <= y < PREVIEW_HEIGHT:
        offset = (y * PREVIEW_WIDTH + x) * 3
        pixels[offset : offset + 3] = bytes(color)


def _draw_rectangle(
    pixels: bytearray,
    bounds: tuple[int, int, int, int],
    color: tuple[int, int, int],
) -> None:
    """Draw a filled rectangle on the preview canvas."""
    left, top, width, height = bounds
    for y in range(top, top + height):
        for x in range(left, left + width):
            _set_pixel(pixels, x, y, color)


def _draw_circle(
    pixels: bytearray,
    center_x: int,
    center_y: int,
    radius: int,
    color: tuple[int, int, int],
) -> None:
    """Draw a filled circle on the preview canvas."""
    radius_squared = radius * radius
    for y in range(center_y - radius, center_y + radius + 1):
        for x in range(center_x - radius, center_x + radius + 1):
            if (x - center_x) ** 2 + (y - center_y) ** 2 <= radius_squared:
                _set_pixel(pixels, x, y, color)


def _draw_text(
    pixels: bytearray,
    text: str,
    position: tuple[int, int],
    color: tuple[int, int, int],
    scale: int = 3,
) -> None:
    """Draw centered uppercase text with the built-in bitmap font."""
    center_x, top = position
    supported_text = "".join(
        character for character in text.upper() if character in _FONT
    )
    character_width = 6 * scale
    left = center_x - (len(supported_text) * character_width - scale) // 2
    for character_index, character in enumerate(supported_text):
        glyph = _FONT[character]
        glyph_left = left + character_index * character_width
        for row_index, row in enumerate(glyph):
            for column_index, pixel in enumerate(row):
                if pixel == "1":
                    _draw_rectangle(
                        pixels,
                        (
                            glyph_left + column_index * scale,
                            top + row_index * scale,
                            scale,
                            scale,
                        ),
                        color,
                    )


def _asset_color(asset_id: str) -> tuple[int, int, int]:
    """Derive a bright stable color from an asset identifier."""
    digest = hashlib.sha256(asset_id.encode()).digest()
    return (
        72 + digest[0] % 128,
        72 + digest[1] % 128,
        72 + digest[2] % 128,
    )


def _render_png(first_id: str, second_id: str) -> bytes:
    """Build a deterministic labeled PNG preview for two assets."""
    background = (255, 250, 242)
    pixels = bytearray(background * (PREVIEW_WIDTH * PREVIEW_HEIGHT))
    first_color = _asset_color(first_id)
    second_color = _asset_color(second_id)
    _draw_circle(pixels, 190, 140, 100, first_color)
    _draw_circle(pixels, 322, 140, 100, second_color)

    first_seed = hashlib.sha256(first_id.encode()).digest()
    second_seed = hashlib.sha256(second_id.encode()).digest()
    for index in range(5):
        _draw_circle(
            pixels,
            145 + first_seed[index] % 90,
            95 + first_seed[index + 5] % 90,
            6 + first_seed[index + 10] % 8,
            (255, 255, 255),
        )
        _draw_rectangle(
            pixels,
            (
                277 + second_seed[index] % 90,
                95 + second_seed[index + 5] % 90,
                9 + second_seed[index + 10] % 10,
                9 + second_seed[index + 10] % 10,
            ),
            (255, 255, 255),
        )

    _draw_rectangle(pixels, (246, 132, 20, 8), (38, 50, 56))
    _draw_rectangle(pixels, (252, 126, 8, 20), (38, 50, 56))
    _draw_text(pixels, first_id[:14], (150, 276), (38, 50, 56), scale=2)
    _draw_text(pixels, second_id[:14], (362, 276), (38, 50, 56), scale=2)

    scanlines = bytearray()
    stride = PREVIEW_WIDTH * 3
    for row in range(PREVIEW_HEIGHT):
        scanlines.append(0)
        start = row * stride
        scanlines.extend(pixels[start : start + stride])

    description = (
        f"Description\0Mock offline preview: {first_id} + {second_id}".encode()
    )
    header = struct.pack(">IIBBBBB", PREVIEW_WIDTH, PREVIEW_HEIGHT, 8, 2, 0, 0, 0)
    return b"".join(
        (
            b"\x89PNG\r\n\x1a\n",
            _png_chunk(b"IHDR", header),
            _png_chunk(b"tEXt", description),
            _png_chunk(b"IDAT", zlib.compress(bytes(scanlines), level=9)),
            _png_chunk(b"IEND", b""),
        )
    )


def write_preview(first: str, second: str, output: str | Path) -> Path:
    """Write a deterministic SVG or PNG preview.

    Args:
        first: First catalog asset identifier.
        second: Second catalog asset identifier.
        output: Destination with an ``.svg`` or ``.png`` suffix.

    Returns:
        The output path.

    Raises:
        CatalogError: If either identifier is absent from the catalog.
        ValueError: If the destination has an unsupported suffix.
    """
    assets = load_catalog()
    asset_by_id(first, assets)
    asset_by_id(second, assets)
    first_id, second_id = normalize_pair(first, second)
    output_path = Path(output)
    suffix = output_path.suffix.lower()
    if suffix == ".svg":
        preview = _render_svg(first_id, second_id)
    elif suffix == ".png":
        preview = _render_png(first_id, second_id)
    else:
        msg = "Output file must use .svg or .png"
        raise ValueError(msg)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(preview)
    return output_path


def _load_store(path: Path) -> CombinationStore:
    """Load an existing store or return an empty one."""
    if not path.exists():
        return CombinationStore(combinations=[])
    try:
        return CombinationStore.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as error:
        msg = f"Combination store is invalid: {path}: {error}"
        raise CombinationStoreError(msg) from error


def record_combination(
    combination: Combination,
    store_path: str | Path | None = None,
) -> Path:
    """Insert or update a combination in the local JSON store.

    Args:
        combination: Validated combination record.
        store_path: Optional path that replaces the default store in the current
            directory.

    Returns:
        The path to the updated store.

    Raises:
        CombinationStoreError: If an existing store is invalid or cannot be written.
    """
    selected_path = (
        Path(store_path)
        if store_path is not None
        else Path.cwd() / ".emojibench" / "combinations.json"
    )
    store = _load_store(selected_path)
    combinations = [
        existing for existing in store.combinations if existing.id != combination.id
    ]
    combinations.append(combination)
    combinations.sort(key=lambda item: item.id)
    updated_store = CombinationStore(combinations=combinations)
    selected_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        selected_path.write_text(
            updated_store.model_dump_json(indent=2),
            encoding="utf-8",
        )
    except OSError as error:
        msg = f"Combination store could not be written: {selected_path}: {error}"
        raise CombinationStoreError(msg) from error
    return selected_path
