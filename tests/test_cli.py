"""Tests for the emojibench command-line interface."""

import json
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]


def run_cli(
    *arguments: str, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """Run the project CLI in a selected working directory."""
    return subprocess.run(
        [
            "uv",
            "run",
            "--project",
            str(PROJECT_ROOT),
            "--frozen",
            "emojibench",
            *arguments,
        ],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )


def test_show_message_cli(my_data: str) -> None:
    """The original scaffold command remains available."""
    output = run_cli("show_message", "--message=Hello terminal!")

    assert "Hello terminal!" in output.stdout


def test_catalog_list_cli_prints_concepts() -> None:
    """The catalog list command prints names and identifiers."""
    output = run_cli("catalog", "list")

    assert "macrophage\tMacrophage\tcells" in output.stdout
    assert "superhero\tSuperhero\tthemes" in output.stdout


def test_catalog_validate_cli_reports_count() -> None:
    """The catalog validate command reports a valid catalog."""
    output = run_cli("catalog", "validate")

    assert output.stdout.strip() == "Catalog is valid: 8 concepts."


def test_combine_cli_writes_preview_and_store(tmp_path: Path) -> None:
    """The combine command writes a preview and records its inputs."""
    output_path = tmp_path / "preview.png"

    output = run_cli(
        "combine",
        "macrophage",
        "superhero",
        "--output",
        str(output_path),
        cwd=tmp_path,
    )

    assert output.stdout.strip() == str(output_path)
    assert output_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    store_path = tmp_path / ".emojibench" / "combinations.json"
    store = json.loads(store_path.read_text(encoding="utf-8"))
    assert store["combinations"][0]["input_ids"] == [
        "macrophage",
        "superhero",
    ]
