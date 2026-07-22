"""GRAP Autopilot API (PRD C4). Draft on crossing, human approves."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from services.api.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_grap_state_reports_current_stage(client):
    r = client.get("/api/v1/cities/delhi/grap")
    assert r.status_code == 200
    d = r.json()
    assert "current_stage" in d and "current_stage_label" in d
    assert "crossing_forecast" in d
    assert isinstance(d["forecast_series"], list)


def test_seeded_draft_is_present_and_carries_measures(client):
    d = client.get("/api/v1/cities/delhi/grap").json()
    draft = d["draft"]
    assert draft is not None, "seeded GRAP draft missing — the C4 card can't render"
    assert draft["measures"], "a draft with no measures is useless"
    assert all(m["citation"] for m in draft["measures"]), "every measure needs a citation"
    assert draft["status"] == "draft", "the autopilot must never present as pre-approved"


def test_approval_requires_the_endpoint_and_is_audited(client):
    from vayu_core.db import read_conn, write_conn

    draft = client.get("/api/v1/cities/delhi/grap").json()["draft"]
    did = draft["id"]
    r = client.post(f"/api/v1/grap/{did}/approve")
    assert r.status_code == 200
    assert r.json()["status"] == "approved"

    with read_conn() as con:
        row = con.execute(
            "SELECT count(*) FROM audit_log WHERE trigger = ?", [f"grap_approved:{did}"]
        ).fetchone()
    assert row[0] >= 1, "approval must leave an audit trail"

    # reset for other tests / demo
    with write_conn() as con:
        con.execute("UPDATE grap_drafts SET status='draft' WHERE id = ?", [did])
        con.execute("DELETE FROM audit_log WHERE trigger LIKE 'grap_%'")


def test_approving_unknown_draft_is_404(client):
    assert client.post("/api/v1/grap/NOPE/approve").status_code == 404
