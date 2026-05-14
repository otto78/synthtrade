"""
backend/tests/integration/test_activate_strategy.py
--------------------------------------------------
Test di integrazione per l'attivazione operativa delle strategie.
Verifica il controllo fondi e l'esecuzione degli ordini.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.dependencies import get_current_user, get_exchange

@pytest.mark.asyncio
async def test_api_connectivity(client):
    """Verifica che le rotte base siano raggiungibili."""
    from app.main import app
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
    
    app.dependency_overrides[get_current_user] = lambda: "user"
    try:
        res = client.get("/api/strategies")
        assert res.status_code == 200
    finally:
        app.dependency_overrides.clear()
        
    res = client.post("/api/strategies/123/activate")
    assert res.status_code == 401

@pytest.mark.asyncio
async def test_activate_strategy_insufficient_funds(client):
    """TASK-403: Verifica errore 422 se il saldo su Binance è insufficiente."""
    from app.main import app
    mock_strategy = {
        "id": "strat_123",
        "status": "APPROVED",
        "budget_eur": 1000.0,
        "pair": "BTC/USDT",
        "params": {}
    }
    
    with patch("app.api.strategies.get_supabase") as mock_get_supabase:
        db = MagicMock()
        mock_get_supabase.return_value = db
        db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [mock_strategy]
        
        mock_exchange = AsyncMock()
        mock_exchange.get_balance.return_value = 500.0 # Saldo insufficiente
        mock_exchange.get_holdings.return_value = {}
        
        app.dependency_overrides[get_current_user] = lambda: "user"
        app.dependency_overrides[get_exchange] = lambda: mock_exchange
        
        try:
            response = client.post("/api/strategies/strat_123/activate")
            assert response.status_code == 422
            # Il formato dell'errore è quello definito in app.core.exceptions
            assert response.json()["message"]["error"] == "insufficient_funds"
        finally:
            app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_activate_strategy_success(client):
    """TASK-402: Verifica attivazione con successo ed esecuzione ordini."""
    from app.main import app
    mock_strategy = {
        "id": "strat_123",
        "status": "APPROVED",
        "budget_eur": 100.0,
        "pair": "BTC/USDT",
        "params": {}
    }
    
    with patch("app.api.strategies.get_supabase") as mock_get_supabase:
        db = MagicMock()
        mock_get_supabase.return_value = db
        db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [mock_strategy]
        db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{"status": "ACTIVE"}]
        db.table.return_value.insert.return_value.execute.return_value.data = [{"id": "trade_1"}]
        
        mock_exchange = AsyncMock()
        mock_exchange.get_balance.return_value = 2000.0
        mock_exchange.get_ticker_price.return_value = 50000.0
        mock_exchange.get_holdings.return_value = {}
        mock_exchange.get_symbol_filters.return_value = {}
        mock_exchange.place_market_order.return_value = {"price": 50000.0, "quantity": 0.002}
        
        app.dependency_overrides[get_current_user] = lambda: "user"
        app.dependency_overrides[get_exchange] = lambda: mock_exchange
        
        try:
            with patch("app.api.strategies.calculate_quantity", return_value=0.002):
                response = client.post("/api/strategies/strat_123/activate")
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "ACTIVE"
                assert len(data["allocation_trades"]) == 1
        finally:
            app.dependency_overrides.clear()
