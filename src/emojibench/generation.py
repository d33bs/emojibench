"""Bounded in-process generation jobs and local asset storage."""

import json
import threading
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutureTimeout
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import Field, ValidationError

from emojibench.models import Asset, NonEmptyString, Slug, StrictModel
from emojibench.providers import GeneratedAsset, ImageProvider

JobState = Literal["queued", "running", "succeeded", "failed"]


class GenerationError(RuntimeError):
    """A generation job or local generation store failed."""


class JobQueueFullError(GenerationError):
    """The bounded in-process job queue has no available slot."""


class GenerationJob(StrictModel):
    """One local image-generation job.

    Attributes:
        id: Stable identifier for this job record.
        input_ids: Source catalog asset identifiers.
        provider: Selected image provider.
        state: Current job state.
        created_at: Time when the job entered the queue.
        started_at: Time when the worker started the job.
        finished_at: Time when the worker completed the job.
        asset_id: Generated asset identifier after success.
        error: Readable failure cause after an error.
    """

    id: Slug
    input_ids: tuple[Slug, Slug]
    provider: NonEmptyString
    state: JobState
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    asset_id: Slug | None = None
    error: str | None = None


class JobStoreDocument(StrictModel):
    """JSON document that contains local generation jobs."""

    schema_version: NonEmptyString = "1.0"
    jobs: list[GenerationJob]


class AssetStoreDocument(StrictModel):
    """JSON document that contains generated asset records."""

    schema_version: NonEmptyString = "1.0"
    assets: list[Asset]


class AssetStore:
    """Store generated images and metadata under one local root.

    Args:
        root: Directory that contains ``assets.json`` and generated files.
    """

    def __init__(self, root: str | Path = ".emojibench") -> None:
        """Set the local store root."""
        self.root = Path(root)
        self.document_path = self.root / "assets.json"
        self._lock = threading.Lock()

    def list(self) -> list[Asset]:
        """Return all generated assets ordered by identifier."""
        return self._load_document().assets

    def get(self, asset_id: str) -> Asset:
        """Return one generated asset.

        Args:
            asset_id: Exact generated asset identifier.

        Returns:
            The matching asset record.

        Raises:
            ValueError: If the store does not contain the identifier.
        """
        for asset in self.list():
            if asset.id == asset_id:
                return asset
        msg = f"Unknown generated asset id '{asset_id}'."
        raise ValueError(msg)

    def save(self, generated: GeneratedAsset) -> Path:
        """Write image bytes, sidecar metadata, and the central asset record.

        Args:
            generated: Generated image and validated draft record.

        Returns:
            The written image path.

        Raises:
            GenerationError: If a local file cannot be written.
        """
        image_path = self.root / generated.asset.image_uri
        if self.root.resolve() not in image_path.resolve().parents:
            msg = f"Generated image path leaves the local store: {image_path}"
            raise GenerationError(msg)
        try:
            image_path.parent.mkdir(parents=True, exist_ok=True)
            image_path.write_bytes(generated.image_bytes)
            self._write_sidecar(generated.asset, image_path.with_suffix(".json"))
            self.update(generated.asset)
        except OSError as error:
            msg = f"Generated asset could not be written: {image_path}: {error}"
            raise GenerationError(msg) from error
        return image_path

    def update(self, asset: Asset) -> None:
        """Update an asset record and its sidecar without changing the image.

        Args:
            asset: Updated generated asset record.

        Raises:
            GenerationError: If the metadata cannot be written.
        """
        image_path = self.root / asset.image_uri
        with self._lock:
            document = self._load_document()
            assets = [item for item in document.assets if item.id != asset.id]
            assets.append(asset)
            assets.sort(key=lambda item: item.id)
            updated = AssetStoreDocument(assets=assets)
            try:
                self.root.mkdir(parents=True, exist_ok=True)
                self.document_path.write_text(
                    updated.model_dump_json(indent=2),
                    encoding="utf-8",
                )
                self._write_sidecar(asset, image_path.with_suffix(".json"))
            except OSError as error:
                msg = f"Generated asset metadata could not be written: {error}"
                raise GenerationError(msg) from error

    @staticmethod
    def load_sidecar(path: str | Path) -> Asset:
        """Load one generated asset sidecar.

        Args:
            path: JSON sidecar path.

        Returns:
            The validated asset record.

        Raises:
            GenerationError: If the sidecar cannot be read or validated.
        """
        selected_path = Path(path)
        try:
            return Asset.model_validate_json(selected_path.read_text(encoding="utf-8"))
        except (OSError, ValidationError) as error:
            msg = f"Generated asset metadata is invalid: {selected_path}: {error}"
            raise GenerationError(msg) from error

    def _load_document(self) -> AssetStoreDocument:
        """Load the central asset document or return an empty document."""
        if not self.document_path.exists():
            return AssetStoreDocument(assets=[])
        try:
            data = json.loads(self.document_path.read_text(encoding="utf-8"))
            return AssetStoreDocument.model_validate(data)
        except (OSError, json.JSONDecodeError, ValidationError) as error:
            msg = f"Generated asset store is invalid: {self.document_path}: {error}"
            raise GenerationError(msg) from error

    @staticmethod
    def _write_sidecar(asset: Asset, path: Path) -> None:
        """Write one asset record beside its image."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(asset.model_dump_json(indent=2), encoding="utf-8")


class GenerationService:
    """Operate a bounded thread worker and persist each job transition.

    Args:
        store_root: Local generation store directory.
        max_workers: Maximum concurrent jobs.
        max_queue: Maximum jobs that can wait behind active workers.
    """

    def __init__(
        self,
        store_root: str | Path = ".emojibench",
        *,
        max_workers: int = 2,
        max_queue: int = 4,
    ) -> None:
        """Initialize the worker, queue bound, and local stores."""
        if max_workers < 1 or max_queue < 0:
            msg = "max_workers must be positive and max_queue cannot be negative."
            raise ValueError(msg)
        self.store_root = Path(store_root)
        self.jobs_path = self.store_root / "jobs.json"
        self.assets = AssetStore(self.store_root)
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="emojibench-generation",
        )
        self._capacity = threading.BoundedSemaphore(max_workers + max_queue)
        self._lock = threading.Lock()
        self._jobs = {job.id: job for job in self._load_jobs().jobs}
        self._futures: dict[str, Future[None]] = {}

    def __enter__(self) -> "GenerationService":
        """Return this active generation service."""
        return self

    def __exit__(self, *_args: object) -> None:
        """Wait for active worker tasks and close the service."""
        self.close()

    def close(self) -> None:
        """Wait for active worker tasks and release worker threads."""
        self._executor.shutdown(wait=True)

    def submit(
        self,
        first: str,
        second: str,
        provider: ImageProvider,
    ) -> GenerationJob:
        """Submit one job without waiting for generation.

        Args:
            first: First catalog asset identifier.
            second: Second catalog asset identifier.
            provider: Configured image provider.

        Returns:
            The persisted queued job.

        Raises:
            JobQueueFullError: If the bounded worker has no capacity.
        """
        if not self._capacity.acquire(blocking=False):
            msg = "The generation queue is full. Wait for an active job to finish."
            raise JobQueueFullError(msg)
        job = GenerationJob(
            id=f"job-{uuid4().hex}",
            input_ids=(first, second),
            provider=provider.name,
            state="queued",
            created_at=datetime.now(UTC),
        )
        try:
            self._replace_job(job)
            future = self._executor.submit(self._run_job, job.id, provider)
            self._futures[job.id] = future
        except Exception:
            self._capacity.release()
            raise
        return job

    def wait(self, job_id: str, *, timeout: float) -> GenerationJob:
        """Wait a bounded time for a submitted job.

        Args:
            job_id: Submitted job identifier.
            timeout: Maximum wait in seconds.

        Returns:
            The succeeded or failed job record.

        Raises:
            GenerationError: If the job is unknown or the wait expires.
        """
        future = self._futures.get(job_id)
        if future is None:
            msg = f"Unknown active generation job '{job_id}'."
            raise GenerationError(msg)
        try:
            future.result(timeout=timeout)
        except FutureTimeout as error:
            msg = f"Generation job '{job_id}' did not finish within {timeout} seconds."
            raise GenerationError(msg) from error
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> GenerationJob:
        """Return a job from the local service state."""
        try:
            return self._jobs[job_id]
        except KeyError as error:
            msg = f"Unknown generation job '{job_id}'."
            raise GenerationError(msg) from error

    def _run_job(self, job_id: str, provider: ImageProvider) -> None:
        """Generate one asset and persist terminal job state."""
        job = self.get_job(job_id)
        running = job.model_copy(
            update={"state": "running", "started_at": datetime.now(UTC)}
        )
        self._replace_job(running)
        try:
            generated = provider.generate(*running.input_ids)
            self.assets.save(generated)
            completed = running.model_copy(
                update={
                    "state": "succeeded",
                    "finished_at": datetime.now(UTC),
                    "asset_id": generated.asset.id,
                }
            )
        except Exception as error:  # Job boundaries must persist all provider errors.
            completed = running.model_copy(
                update={
                    "state": "failed",
                    "finished_at": datetime.now(UTC),
                    "error": f"{type(error).__name__}: {error}",
                }
            )
        finally:
            self._capacity.release()
        self._replace_job(completed)

    def _replace_job(self, job: GenerationJob) -> None:
        """Insert one job state and rewrite the local job document."""
        with self._lock:
            self._jobs[job.id] = job
            document = JobStoreDocument(
                jobs=sorted(self._jobs.values(), key=lambda item: item.created_at)
            )
            try:
                self.store_root.mkdir(parents=True, exist_ok=True)
                self.jobs_path.write_text(
                    document.model_dump_json(indent=2),
                    encoding="utf-8",
                )
            except OSError as error:
                msg = f"Generation job store could not be written: {error}"
                raise GenerationError(msg) from error

    def _load_jobs(self) -> JobStoreDocument:
        """Load existing jobs or return an empty job document."""
        if not self.jobs_path.exists():
            return JobStoreDocument(jobs=[])
        try:
            return JobStoreDocument.model_validate_json(
                self.jobs_path.read_text(encoding="utf-8")
            )
        except (OSError, ValidationError) as error:
            msg = f"Generation job store is invalid: {self.jobs_path}: {error}"
            raise GenerationError(msg) from error
