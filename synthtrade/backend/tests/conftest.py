import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

@pytest.fixture
def mock_supabase():
    with patch("app.db.supabase_client.get_supabase") as mock:
        db = MagicMock()
        mock.return_value = db
        yield db

@pytest.fixture
def client(mock_supabase):
    from app.main import app
    return TestClient(app)
