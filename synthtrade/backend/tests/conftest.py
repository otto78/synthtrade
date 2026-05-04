import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_supabase():
    with patch("app.db.supabase_client.get_supabase") as mock:
        db = MagicMock()
        mock.return_value = db
        yield db
