from fastapi.testclient import TestClient

from app.db.session import init_db
from app.main import app

init_db()
client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_recommendation_endpoint():
    payload = {
        "metrics": {
            "resource_id": "db-9", "resource_type": "database",
            "current_version": "15.2", "target_version": "15.6",
            "criticality": "MEDIUM", "error_rate": 0.01, "cpu_p95": 40,
            "hourly_usage": [{"hour": h, "utilization": 50} for h in range(24)],
        }
    }
    r = client.post("/api/v1/recommendations?persist=false", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["resource_id"] == "db-9"
    assert body["recommended_strategy"] in {"CANARY", "LINEAR", "ALL_AT_ONCE"}
    assert 0.0 <= body["risk_score"] <= 1.0
