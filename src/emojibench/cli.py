"""Command-line interface for emojibench."""

import json
from pathlib import Path

import fire

from emojibench.catalog import load_catalog, public_catalog
from emojibench.combinations import (
    combination_id,
    create_combination,
    record_combination,
    write_preview,
)
from emojibench.evaluation import evaluate_asset
from emojibench.generation import AssetStore, GenerationService
from emojibench.main import show_message
from emojibench.providers import get_provider
from emojibench.review import approve_asset, list_drafts, reject_asset
from emojibench.stories import compose_story, save_story


class CatalogCLI:
    """Commands for the bundled offline catalog."""

    def list(self, store: str | None = None) -> None:
        """Print public asset identifiers, names, and categories.

        Args:
            store: Optional generated-asset store directory. When set,
                approved generated assets are listed too.
        """
        if store is None:
            assets = load_catalog()
        else:
            assets = public_catalog(store)
        for asset in assets:
            print(f"{asset.id}\t{asset.name}\t{asset.category}")

    def validate(self) -> None:
        """Validate the catalog and its local image files."""
        assets = load_catalog()
        print(f"Catalog is valid: {len(assets)} concepts.")


class ReviewCLI:
    """Guarded human review of generated assets."""

    def list(self, store: str = ".emojibench") -> None:
        """Print generated draft assets that await review."""
        drafts = list_drafts(store_root=store)
        if not drafts:
            print("No drafts awaiting review.")
            return
        for asset in drafts:
            print(f"{asset.id}\t{asset.name}\tdraft")

    def approve(
        self,
        asset_id: str,
        reviewer: str = "",
        store: str = ".emojibench",
    ) -> None:
        """Approve one generated draft after human review."""
        asset = approve_asset(asset_id, reviewer=reviewer, store_root=store)
        print(f"Approved {asset.id} (reviewer: {reviewer}).")

    def reject(
        self,
        asset_id: str,
        reviewer: str = "",
        reason: str = "",
        store: str = ".emojibench",
    ) -> None:
        """Reject one generated draft with a required reason."""
        asset = reject_asset(
            asset_id,
            reviewer=reviewer,
            reason=reason,
            store_root=store,
        )
        print(f"Rejected {asset.id} (reviewer: {reviewer}).")


class StoryCLI:
    """Commands for composing and exporting visual stories."""

    def create(
        self,
        story_file: str,
        store: str = ".emojibench",
        output: str | None = None,
    ) -> None:
        """Compose a story from a JSON description and export it.

        Args:
            story_file: Path to a JSON file with title, audience, and
                ordered panels.
            store: Local generated-asset store directory.
            output: Optional export directory. Defaults to
                `.emojibench/stories/<story-id>/`.
        """
        source = Path(story_file)
        document = json.loads(source.read_text(encoding="utf-8"))
        story = compose_story(
            document["title"],
            document["audience"],
            document["panels"],
            store_root=store,
        )
        destination = (
            Path(output)
            if output is not None
            else Path(store) / "stories" / story.id
        )
        json_path = save_story(story, destination)
        print(json_path)


class emojibenchCLI:
    """Top-level commands for emojibench."""

    def __init__(self) -> None:
        """Expose the command groups."""
        self.catalog = CatalogCLI()
        self.review = ReviewCLI()
        self.story = StoryCLI()

    def show_message(
        self,
        message: str = "Hello, world!",
    ) -> None:
        """Print the scaffold example message.

        Args:
            message: Message to print.
        """
        print(show_message(message=message))

    def combine(
        self,
        first: str,
        second: str,
        output: str | None = None,
    ) -> None:
        """Create and record a deterministic mock preview.

        Args:
            first: First catalog asset identifier.
            second: Second catalog asset identifier.
            output: Optional SVG or PNG destination.
        """
        output_path = (
            output
            if output is not None
            else f".emojibench/previews/{combination_id(first, second)}.svg"
        )
        combination = create_combination(first, second)
        written_path = write_preview(first, second, output_path)
        record_combination(combination)
        print(written_path)

    def generate(
        self,
        first: str,
        second: str,
        provider: str | None = None,
        store: str = ".emojibench",
        timeout: float = 120.0,
    ) -> None:
        """Generate a draft asset for two catalog concepts.

        Args:
            first: First catalog asset identifier.
            second: Second catalog asset identifier.
            provider: Optional 'mock' or 'openai' provider override.
            store: Local generation store directory.
            timeout: Maximum seconds to wait for the job.
        """
        selected_provider = get_provider(provider)
        store_path = Path(store)
        with GenerationService(store_root=store_path) as service:
            job = service.submit(first, second, selected_provider)
            finished = service.wait(job.id, timeout=timeout)
        if finished.asset_id is None:
            detail = finished.error or "unknown error"
            msg = f"Generation failed: {detail}"
            raise SystemExit(msg)
        asset = AssetStore(store_path).get(finished.asset_id)
        image_path = store_path / asset.image_uri
        print(f"{asset.id}\t{image_path}")

    def evaluate(
        self,
        path: str,
        store: str | None = None,
    ) -> None:
        """Print a deterministic pass or fail report for one image.

        Args:
            path: Generated PNG or SVG file to evaluate.
            store: Optional local generation store directory.
        """
        result = evaluate_asset(path, store_root=store)
        for check in result.checks:
            state = "PASS" if check.passed else "FAIL"
            print(f"{state}\t{check.name}\t{check.detail}")
        verdict = "passed" if result.passed else "failed"
        print(f"Evaluation {verdict}: {result.path}")


def trigger() -> None:
    """Start the Fire command-line interface."""
    fire.Fire(emojibenchCLI)
