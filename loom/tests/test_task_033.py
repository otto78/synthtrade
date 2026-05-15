"""
Tests for TASK-033: Refactor supabase_client.py (Singleton/Dependency)
"""

def test_get_supabase_singleton():
    from synthtrade.backend.app.db.supabase_client import get_supabase
    client1 = get_supabase()
    client2 = get_supabase()
    assert client1 is client2

def test_dependency_exists():
    try:
        from synthtrade.backend.app.dependencies import get_db
        assert callable(get_db)
    except ImportError:
        assert False, "get_db dependency not found"
