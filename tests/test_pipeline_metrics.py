"""Tests for the pipeline metrics endpoint.

The endpoint `/api/pipeline/metrics/{generation_id}` should return the
metrics stored in the `generation_metrics` table.  Because the test suite
runs against a local Supabase instance (or a mock), we only verify the
behaviour for a non‑existent generation_id – the endpoint must return a
404 error.
"""

import uuid
from fastapi.testclient import TestClient
from synthtrade.backend.app.main import app
from synthtrade.backend.app.dependencies import get_current_user

# Override the auth dependency for testing
def _test_user_override():
    return "test_user"

app.dependency_overrides[get_current_user] = _test_user_override

client = TestClient(app)


def test_metrics_endpoint_not_found():
    # Use a random UUID that surely does not exist in the DB
    unknown_id = str(uuid.uuid4())
    response = client.get(f"/api/pipeline/metrics/{unknown_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Metrics not found for this generation"
