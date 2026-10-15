"""Real API composition, authorization and PostgreSQL novelty round trips."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from researchbase.api.app import create_app
from researchbase.application.novelty import RecordSearchCoverageCommand

pytest_plugins = ("tests.integration.phase2.pr2_18_fixtures",)


@pytest.mark.parametrize("credential_state", ["missing", "valid", "revoked"])
def test_novelty_endpoint_with_composed_services(
    novelty_env, monkeypatch, tmp_path, credential_state
):
    e = novelty_env
    coverage = e["service"].record_search_coverage(
        e["author"],
        RecordSearchCoverageCommand(
            uuid4(), e["project"], e["plan"], e["executions"], "Selected scope."
        ),
    )
    monkeypatch.setenv("ARTIFACT_STORE_ROOT", str(tmp_path / "api-artifacts"))
    app = create_app()
    # Keep the production None wiring for the missing-verifier case. The other
    # cases model a configured credential verifier at the same boundary.
    if credential_state != "missing":
        monkeypatch.setattr(app.state.services.novelty, "_credentials", e["credentials"])
        e["credentials"].enabled = credential_state == "valid"

    @app.middleware("http")
    async def inject_principal(request, call_next):
        request.state.verified_principal = e["author"]
        return await call_next(request)

    identity = uuid4()
    base = f"/v1/projects/{e['project']}/novelty-assessments"
    body = {
        "id": str(identity),
        "claim_version_id": str(e["claim"]),
        "search_coverage_id": str(coverage.id),
        "assessment": "INCONCLUSIVE",
        "limitations": "Selected scope; no screening.",
    }
    with TestClient(app) as client:
        response = client.post(base, json=body)
        read = client.get(f"{base}/{identity}")
        if credential_state == "valid":
            assert response.status_code == read.status_code == 200
            saved = response.json()
            assert saved["id"] == str(identity)
            assert saved["assessed_by"] == str(e["author"].actor_id)
            assert saved["assessment"] == "INCONCLUSIVE"
            assert read.json()["content_hash"] == saved["content_hash"]
            replay = client.post(base, json=body)
            assert replay.status_code == 200
            assert replay.json()["content_hash"] == saved["content_hash"]
        else:
            assert response.status_code == read.status_code == 403
            assert response.json()["error"]["code"] == "FORBIDDEN"
            assert read.json()["error"]["code"] == "FORBIDDEN"
    with e["engine"].connect() as conn:
        count = conn.execute(
            text("SELECT count(*) FROM novelty_assessments WHERE id=:id"), {"id": identity}
        ).scalar_one()
        assert count == (1 if credential_state == "valid" else 0)
