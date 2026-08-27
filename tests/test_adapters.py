from fastapi.testclient import TestClient

from researchbase.api.app import app


def test_fastapi_health_smoke() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
