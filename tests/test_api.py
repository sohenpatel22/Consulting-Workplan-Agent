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
    data = response.json()
    assert data["status"] == "ok"
    assert "configured_model" in data
    assert "model" in data
    assert "provider" in data
    assert "ready" in data


def test_index_page(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def _confirm_open_questions(client: TestClient, session_id: str, data: dict) -> None:
    questions = data.get("confirmation_questions") or []
    if not questions:
        return
    answers = [
        {"question": question, "answer": f"Confirmed for planning: {question}"}
        for question in questions
    ]
    response = client.post(
        f"/api/sessions/{session_id}/confirm",
        json={"answers": answers},
    )
    assert response.status_code == 202, response.text


def _wait_for_complete(client: TestClient, session_id: str) -> dict:
    data: dict = {}
    for _ in range(120):
        response = client.get(f"/api/sessions/{session_id}")
        assert response.status_code == 200
        data = response.json()
        if data.get("awaiting_confirmation") or data.get("phase") == "awaiting_confirmation":
            _confirm_open_questions(client, session_id, data)
            continue
        if data["job_status"] in ("complete", "failed"):
            break
        time.sleep(0.05)
    return data


def test_warm_build_cache_while_awaiting_confirmation(client: TestClient) -> None:
    create = client.post(
        "/api/sessions",
        json={"brief_text": BRIEF, "mock": True},
    )
    session_id = create.json()["session_id"]

    for _ in range(120):
        response = client.get(f"/api/sessions/{session_id}")
        data = response.json()
        if data.get("phase") == "awaiting_confirmation":
            warm = client.post(f"/api/sessions/{session_id}/warm-build-cache")
            assert warm.status_code == 204
            return
        if data["job_status"] == "failed":
            pytest.fail(data.get("error"))
        time.sleep(0.05)
    pytest.fail("Session never reached awaiting_confirmation")


def test_warm_build_cache_rejects_wrong_phase(client: TestClient) -> None:
    create = client.post(
        "/api/sessions",
        json={"brief_text": BRIEF, "mock": True},
    )
    session_id = create.json()["session_id"]
    _wait_for_complete(client, session_id)
    response = client.post(f"/api/sessions/{session_id}/warm-build-cache")
    assert response.status_code == 400


def test_open_questions_pause_before_build(client: TestClient) -> None:
    create = client.post(
        "/api/sessions",
        json={"brief_text": BRIEF, "mock": True},
    )
    session_id = create.json()["session_id"]

    paused: dict | None = None
    for _ in range(120):
        response = client.get(f"/api/sessions/{session_id}")
        data = response.json()
        if data.get("phase") == "awaiting_confirmation":
            paused = data
            break
        if data["job_status"] == "failed":
            pytest.fail(data.get("error"))
        time.sleep(0.05)

    assert paused is not None
    assert paused["awaiting_confirmation"] is True
    assert len(paused["confirmation_questions"]) >= 1
    assert paused["parse_preview"] is not None
    assert paused["wbs"] is None
    assert paused["raid"] is None

    _confirm_open_questions(client, session_id, paused)
    final = _wait_for_complete(client, session_id)
    assert final["job_status"] == "complete"
    assert final["wbs"] is not None


def test_session_response_exposes_partial_artifacts(client: TestClient) -> None:
    from workplan_agent.api.schemas import CreateSessionRequest
    from workplan_agent.api.service import create_session, get_store, session_to_response
    from workplan_agent.llm.fixtures import PARSED_BRIEF_FIXTURE, RAID_FIXTURE, WBS_FIXTURE
    from workplan_agent.models.brief import ParsedBrief
    from workplan_agent.models.raid import RAIDLog
    from workplan_agent.models.wbs import WBS

    record = create_session(CreateSessionRequest(brief_text=BRIEF, mock=True))
    record.session.parsed_brief = ParsedBrief.model_validate(PARSED_BRIEF_FIXTURE)
    record.session.wbs = WBS.model_validate(WBS_FIXTURE)
    record.job_status = "running"
    record.phase = "generating_raid"
    get_store().update(
        record.session.session_id,
        session=record.session,
        job_status="running",
        phase="generating_raid",
    )

    data = session_to_response(record)
    assert data.wbs_html
    assert data.raid_html is None
    assert data.stakeholder_html is None
    assert data.summary is not None
    assert data.summary.wbs_items > 0
    assert data.summary.raid_risks == 0

    record.session.raid = RAIDLog.model_validate(RAID_FIXTURE)
    record.phase = "generating_stakeholder"
    data = session_to_response(record)
    assert data.raid_html
    assert data.stakeholder_html is None


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


def test_review_blocks_same_artifact_in_progress(client: TestClient) -> None:
    create = client.post("/api/sessions", json={"brief_text": BRIEF, "mock": True})
    session_id = create.json()["session_id"]
    _wait_for_complete(client, session_id)

    from workplan_agent.api.store import get_store

    get_store().add_revision_in_progress(session_id, "wbs")
    review = client.post(
        f"/api/sessions/{session_id}/review",
        json={"action": "wbs", "feedback": "Add integration testing phase."},
    )
    assert review.status_code == 409


def test_concurrent_revision_different_artifacts(client: TestClient) -> None:
    create = client.post("/api/sessions", json={"brief_text": BRIEF, "mock": True})
    session_id = create.json()["session_id"]
    _wait_for_complete(client, session_id)

    from workplan_agent.api.store import get_store

    get_store().add_revision_in_progress(session_id, "wbs")
    review = client.post(
        f"/api/sessions/{session_id}/review",
        json={"action": "stakeholder", "feedback": "Add a steering committee row."},
    )
    assert review.status_code == 202


def test_quality_check_after_revision(client: TestClient) -> None:
    create = client.post("/api/sessions", json={"brief_text": BRIEF, "mock": True})
    session_id = create.json()["session_id"]
    _wait_for_complete(client, session_id)

    revision = client.post(
        f"/api/sessions/{session_id}/review",
        json={"action": "wbs", "feedback": "Add integration testing phase."},
    )
    assert revision.status_code == 202
    after = _wait_for_review(client, session_id)
    assert after["quality_gates_stale"] is True
    assert "raid" in after["stale_artifacts"]

    check = client.post(
        f"/api/sessions/{session_id}/review",
        json={"action": "quality_check"},
    )
    assert check.status_code == 200
    refreshed = client.get(f"/api/sessions/{session_id}").json()
    assert refreshed["quality_gates_stale"] is False
    assert "quality_gates" not in refreshed.get("stale_artifacts", {})
