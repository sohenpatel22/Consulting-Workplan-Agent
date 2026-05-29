import time

import pytest
from fastapi.testclient import TestClient

from workplan_agent.api.app import app
from workplan_agent.api.store import reset_store

BRIEF = """# Test Brief

**Client:** Acme Corp
**Project:** Platform Rollout

## Objectives

1. Deliver MVP
2. Train operations team
"""


@pytest.fixture
def client() -> TestClient:
    reset_store()
    return TestClient(app)


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_index_page(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def _wait_for_complete(client: TestClient, session_id: str) -> dict:
    data: dict = {}
    for _ in range(120):
        response = client.get(f"/api/sessions/{session_id}")
        assert response.status_code == 200
        data = response.json()
        if data["job_status"] in ("complete", "failed"):
            break
        time.sleep(0.05)
    return data


def test_create_session_mock(client: TestClient) -> None:
    response = client.post(
        "/api/sessions",
        json={"brief_text": BRIEF, "mock": True},
    )
    assert response.status_code == 202
    session_id = response.json()["session_id"]

    data = _wait_for_complete(client, session_id)
    assert data["job_status"] == "complete", data.get("error")
    assert data["wbs"] is not None
    assert data["raid"] is not None
    assert data["wbs_markdown"]
    assert data["wbs_html"]
    assert "<table>" in data["wbs_html"] or "<h" in data["wbs_html"]
    assert data["raid_html"]
    assert data["status"] == "under_review"
    assert data["unlimited_revisions"] is True
    assert data["revisions_remaining"] is None


def test_review_approve(client: TestClient) -> None:
    create = client.post("/api/sessions", json={"brief_text": BRIEF, "mock": True})
    session_id = create.json()["session_id"]
    _wait_for_complete(client, session_id)

    review = client.post(
        f"/api/sessions/{session_id}/review",
        json={"action": "approve"},
    )
    assert review.status_code == 200
    assert review.json()["status"] == "approved"

    session = client.get(f"/api/sessions/{session_id}").json()
    assert session["status"] == "approved"


def _wait_for_review(client: TestClient, session_id: str) -> dict:
    data: dict = {}
    for _ in range(120):
        response = client.get(f"/api/sessions/{session_id}")
        data = response.json()
        if not data.get("review_in_progress"):
            break
        time.sleep(0.05)
    return data


def test_review_revision(client: TestClient) -> None:
    create = client.post("/api/sessions", json={"brief_text": BRIEF, "mock": True})
    session_id = create.json()["session_id"]
    before = _wait_for_complete(client, session_id)
    wbs_count_before = before["summary"]["wbs_items"]

    review = client.post(
        f"/api/sessions/{session_id}/review",
        json={"action": "wbs", "feedback": "Add a testing work stream under Build."},
    )
    assert review.status_code == 202
    assert review.json()["status"] == "accepted"

    after = _wait_for_review(client, session_id)
    assert after["revision_count"] == 1
    assert after["summary"]["wbs_items"] == wbs_count_before + 1
    assert after.get("last_diff") is not None


def test_mock_raid_revision_enriches_existing_item(client: TestClient) -> None:
    create = client.post("/api/sessions", json={"brief_text": BRIEF, "mock": True})
    session_id = create.json()["session_id"]
    before = _wait_for_complete(client, session_id)
    risks_before = before["summary"]["raid_risks"]

    client.post(
        f"/api/sessions/{session_id}/review",
        json={"action": "raid", "feedback": "more details in descriptions in R1"},
    )
    after = _wait_for_review(client, session_id)
    assert after["summary"]["raid_risks"] == risks_before
    r1 = next(i for i in after["raid"]["risks"] if i["id"] == "R1")
    assert "Expanded per review" in r1["description"]
    assert "more details in descriptions" not in r1["title"]


def test_review_blocks_while_in_progress(client: TestClient) -> None:
    create = client.post("/api/sessions", json={"brief_text": BRIEF, "mock": True})
    session_id = create.json()["session_id"]
    _wait_for_complete(client, session_id)

    from workplan_agent.api.store import get_store

    get_store().update(session_id, review_in_progress=True)
    review = client.post(
        f"/api/sessions/{session_id}/review",
        json={"action": "approve"},
    )
    assert review.status_code == 409
