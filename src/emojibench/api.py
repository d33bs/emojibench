"""FastAPI application exposing emojibench over HTTP."""

from collections.abc import Mapping
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from emojibench.catalog import asset_by_id, load_catalog, public_catalog
from emojibench.combinations import combination_id, record_combination
from emojibench.generation import AssetStore, GenerationService
from emojibench.models import Asset, Story
from emojibench.providers import ImageProvider, get_provider
from emojibench.review import approve_asset, list_drafts, reject_asset
from emojibench.stories import compose_story, save_story


def create_app(
    store_root: str | Path = ".emojibench",
    environ: Mapping[str, str] | None = None,
    max_workers: int = 2,
    max_queue: int = 4,
) -> FastAPI:
    """Build one configured FastAPI application.

    Args:
        store_root: Local generation store directory.
        environ: Optional environment override for provider selection.
        max_workers: Maximum concurrent generation jobs.
        max_queue: Maximum waiting jobs.

    Returns:
        A FastAPI application bound to one generation service.
    """
    app = FastAPI(title="emojibench", version="1.0")
    store_path = Path(store_root)
    service = GenerationService(
        store_root=store_path,
        max_workers=max_workers,
        max_queue=max_queue,
    )
    lock = Lock()

    class GenerationRequest(BaseModel):
        """JSON body for a generation request."""

        first: str
        second: str
        provider: str | None = None

    class StoryRequest(BaseModel):
        """JSON body for a story request."""

        title: str
        audience: str
        panels: list[dict[str, object]] = Field(min_length=1)

    class ReviewRequest(BaseModel):
        """JSON body for a review decision."""

        reviewer: str
        reason: str | None = None

    def _provider(name: str | None) -> ImageProvider:
        try:
            return get_provider(name, environ=environ)
        except Exception as error:
            raise HTTPException(
                status_code=400,
                detail=f"Provider configuration error: {error}",
            ) from error

    def _story_response(story: Story) -> dict[str, object]:
        export_dir = store_path / "stories" / story.id
        json_path = save_story(story, export_dir)
        return {
            "story": story.model_dump(mode="json"),
            "export": str(json_path),
        }

    @app.get("/api/assets")
    def list_assets() -> list[dict[str, object]]:
        """List public assets: approved bundled and generated assets."""
        return [
            asset.model_dump(mode="json")
            for asset in public_catalog(store_path)
        ]

    @app.get("/api/assets/{asset_id}")
    def get_asset(asset_id: str) -> dict[str, object]:
        """Return one bundled catalog asset."""
        try:
            asset = asset_by_id(asset_id)
        except ValueError as error:
            raise HTTPException(
                status_code=404, detail=str(error)
            ) from error
        return asset.model_dump(mode="json")

    @app.get("/api/combinations")
    def get_combination(first: str, second: str) -> dict[str, object]:
        """Return the combination record for two asset identifiers."""
        try:
            asset_by_id(first)
            asset_by_id(second)
        except ValueError as error:
            raise HTTPException(
                status_code=404, detail=str(error)
            ) from error
        return {
            "id": combination_id(first, second),
            "input_ids": sorted((first, second)),
        }

    @app.post("/api/generations")
    def create_generation(
        request: GenerationRequest,
    ) -> dict[str, object]:
        """Queue one generation job for two approved assets."""
        for asset_id in (request.first, request.second):
            try:
                asset_by_id(asset_id)
            except ValueError as error:
                raise HTTPException(
                    status_code=404, detail=str(error)
                ) from error
        selected_provider = _provider(request.provider)
        try:
            with lock:
                job = service.submit(
                    request.first,
                    request.second,
                    selected_provider,
                )
        except Exception as error:
            raise HTTPException(
                status_code=503, detail=str(error)
            ) from error
        return job.model_dump(mode="json")

    @app.get("/api/generations/{job_id}")
    def get_generation(job_id: str) -> dict[str, object]:
        """Return the status of one generation job."""
        try:
            job = service.get_job(job_id)
        except Exception as error:
            raise HTTPException(
                status_code=404, detail=str(error)
            ) from error
        response: dict[str, object] = job.model_dump(mode="json")
        if job.asset_id is not None:
            asset = AssetStore(store_path).get(job.asset_id)
            response["asset"] = asset.model_dump(mode="json")
            response["image_path"] = str(store_path / asset.image_uri)
        return response

    @app.get("/api/review/drafts")
    def review_drafts() -> list[dict[str, object]]:
        """List generated drafts awaiting human review."""
        return [
            asset.model_dump(mode="json")
            for asset in list_drafts(store_root=store_path)
        ]

    @app.post("/api/review/{asset_id}/approve")
    def review_approve(
        asset_id: str,
        request: ReviewRequest,
    ) -> dict[str, object]:
        """Approve one draft after explicit human review."""
        try:
            asset = approve_asset(
                asset_id, reviewer=request.reviewer, store_root=store_path
            )
        except ValueError as error:
            status = 404 if "Unknown" in str(error) else 409
            raise HTTPException(status_code=status, detail=str(error)) from error
        return asset.model_dump(mode="json")

    @app.post("/api/review/{asset_id}/reject")
    def review_reject(
        asset_id: str,
        request: ReviewRequest,
    ) -> dict[str, object]:
        """Reject one draft with a required reason."""
        if not request.reason:
            raise HTTPException(
                status_code=400,
                detail="Rejection reason is required.",
            )
        try:
            asset = reject_asset(
                asset_id,
                reviewer=request.reviewer,
                reason=request.reason or "",
                store_root=store_path,
            )
        except ValueError as error:
            status = 404 if "Unknown" in str(error) else 409
            raise HTTPException(status_code=status, detail=str(error)) from error
        return asset.model_dump(mode="json")

    @app.post("/api/stories")
    def create_story(request: StoryRequest) -> dict[str, object]:
        """Compose and export one story from approved assets."""
        try:
            story = compose_story(
                request.title,
                request.audience,
                request.panels,
                store_root=store_path,
            )
        except ValueError as error:
            raise HTTPException(
                status_code=422, detail=str(error)
            ) from error
        return _story_response(story)

    return app


app = create_app()
