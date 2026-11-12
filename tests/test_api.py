"""Tests for the FastAPI application."""

from pathlib import Path

import pytest

from emojibench.api import create_app

pytest.importorskip("fastapi.testclient")


@pytest.fixture()
def client(tmp_path: Path):
    """Return a test client bound to a temporary store."""
    import fastapi.testclient as ftc

    application = create_app(store_root=tmp_path / ".emojibench")
    with ftc.TestClient(application) as test_client:
        yield test_client


def _wait_for_job(client, job_id: str) -> dict:
    """Poll one job until it reaches a terminal state."""
    import time

    for _ in range(50):
        response = client.get(f"/api/generations/{job_id}")
        assert response.status_code == 200
        job = response.json()
        if job["state"] in ("succeeded", "failed"):
            return job
        time.sleep(0.1)
    raise AssertionError("job did not finish in time")


def test_list_assets_returns_bundled_catalog(client) -> None:
    """The assets endpoint lists the bundled approved concepts."""
    response = client.get("/api/assets")
    assert response.status_code == 200
    assets = response.json()
    ids = {asset["id"] for asset in assets}
    assert {"macrophage", "superhero"} <= ids


def test_get_asset_and_404(client) -> None:
    """Single asset lookups succeed and missing ones 404."""
    response = client.get("/api/assets/macrophage")
    assert response.status_code == 200
    assert response.json()["id"] == "macrophage"

    missing = client.get("/api/assets/missing")
    assert missing.status_code == 404


def test_generation_job_lifecycle(client) -> None:
    """A mock generation job runs and produces a draft asset."""
    response = client.post(
        "/api/generations",
        json={
            "first": "macrophage",
            "second": "superhero",
            "provider": "mock",
        },
    )
    assert response.status_code == 200
    job = response.json()
    assert job["state"] in ("queued", "running")

    finished = _wait_for_job(client, job["id"])
    assert finished["state"] == "succeeded"
    assert finished["asset"]["status"] == "draft"

    drafts = client.get("/api/review/drafts").json()
    assert finished["asset_id"] in {draft["id"] for draft in drafts}


def test_generation_rejects_unknown_asset(client) -> None:
    """Generation with an unknown input returns 404."""
    response = client.post(
        "/api/generations",
        json={"first": "macrophage", "second": "nope", "provider": "mock"},
    )
    assert response.status_code == 404


def test_generation_rejects_unknown_provider(client) -> None:
    """An unknown provider name returns a 400 with a clear message."""
    response = client.post(
        "/api/generations",
        json={"first": "macrophage", "second": "superhero", "provider": "x"},
    )
    assert response.status_code == 400
    assert "Unknown provider" in response.json()["detail"]


def test_review_approve_flow(client) -> None:
    """Approve moves a draft into the public asset list."""
    job = client.post(
        "/api/generations",
        json={
            "first": "macrophage",
            "second": "superhero",
            "provider": "mock",
        },
    ).json()
    finished = _wait_for_job(client, job["id"])
    asset_id = finished["asset_id"]
    assert asset_id is not None

    approve = client.post(
        f"/api/review/{asset_id}/approve",
        json={"reviewer": "Dave Bunten"},
    )
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"

    repeat = client.post(
        f"/api/review/{asset_id}/approve",
        json={"reviewer": "Dave Bunten"},
    )
    assert repeat.status_code == 409

    public = client.get("/api/assets").json()
    assert asset_id in {asset["id"] for asset in public}


def test_review_reject_requires_reason(client) -> None:
    """Rejection without a reason returns 400."""
    job = client.post(
        "/api/generations",
        json={
            "first": "macrophage",
            "second": "superhero",
            "provider": "mock",
        },
    ).json()
    finished = _wait_for_job(client, job["id"])
    asset_id = finished["asset_id"]
    assert asset_id is not None

    missing_reason = client.post(
        f"/api/review/{asset_id}/reject",
        json={"reviewer": "Dave Bunten"},
    )
    assert missing_reason.status_code == 400

    rejected = client.post(
        f"/api/review/{asset_id}/reject",
        json={"reviewer": "Dave Bunten", "reason": "Off brief."},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    public = client.get("/api/assets").json()
    assert asset_id not in {asset["id"] for asset in public}


def test_story_endpoint_creates_and_exports(client, tmp_path: Path) -> None:
    """The story endpoint composes, validates, and exports a story."""
    panels = [
        {
            "asset_id": "macrophage",
            "caption": "Meet the macrophage.",
            "evidence_status": "creative_analogy",
        },
        {
            "asset_id": "petri-dish",
            "caption": "A germ shows up.",
            "evidence_status": "creative_analogy",
        },
        {
            "asset_id": "superhero",
            "caption": "The macrophage saves the day.",
            "evidence_status": "creative_analogy",
        },
    ]
    response = client.post(
        "/api/stories",
        json={
            "title": "A Macrophage Saves the Day",
            "audience": "kids",
            "panels": panels,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["story"]["id"] == "a-macrophage-saves-the-day"
    export = Path(body["export"])
    assert export.is_file()


def test_story_endpoint_rejects_unapproved_assets(client) -> None:
    """A story panel with an unknown asset returns 422."""
    response = client.post(
        "/api/stories",
        json={
            "title": "Bad story",
            "audience": "kids",
            "panels": [
                {
                    "asset_id": "not-an-asset",
                    "caption": "Nope.",
                    "evidence_status": "creative_analogy",
                },
                {
                    "asset_id": "petri-dish",
                    "caption": "Two.",
                    "evidence_status": "creative_analogy",
                },
                {
                    "asset_id": "superhero",
                    "caption": "Three.",
                    "evidence_status": "creative_analogy",
                },
            ],
        },
    )
    assert response.status_code == 422


def test_combination_endpoint(client) -> None:
    """The combination endpoint normalizes the input order."""
    response = client.get(
        "/api/combinations",
        params={"first": "superhero", "second": "macrophage"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["input_ids"] == ["macrophage", "superhero"]
