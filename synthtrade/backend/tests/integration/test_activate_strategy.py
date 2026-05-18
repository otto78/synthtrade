"""
backend/tests/integration/test_activate_strategy.py
--------------------------------------------------
Test di integrazione per l'attivazione operativa delle strategie.
Verifica il controllo fondi e l'esecuzione degli ordini.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.dependencies import get_current_user, get_exchange, get_db
from app.main import app

@pytest.fixture
def mock_db():
    db = MagicMock()
    return db

@pytest.mark.asyncio
async def test_api_connectivity(client):
    """Verifica che le rotte base siano raggiungibili."""
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
    
    app.dependency_overrides[get_current_user] = lambda: "user"
    try:
        app.dependency_overrides[get_db] = lambda: MagicMock()
        res = client.get("/api/strategies")
        assert res.status_code == 200
    finally:
        app.dependency_overrides.clear()
        
    res = client.post("/api/strategies/123/activate")
    assert res.status_code == 401

@pytest.mark.asyncio
async def test_activate_strategy_insufficient_funds(client, mock_db):
    """TASK-403: Verifica errore 422 se il saldo su Binance è insufficiente."""
    mock_strategy = {
        "id": "strat_123",
        "title": "Test Strategy",
        "pair": "BTC/USDT",
        "timeframe": "1h",
        "params": {},
        "budget_eur": 1000.0,
        "status": "APPROVED",
        "score": 0.5
    }
    
    exec_res = MagicMock()
    exec_res.data = mock_strategy
    mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = exec_res
    
    mock_exchange = AsyncMock()
    mock_exchange.get_balance.return_value = 500.0
    mock_exchange.get_holdings.return_value = {}
    
    app.dependency_overrides[get_current_user] = lambda: "user"
    app.dependency_overrides[get_exchange] = lambda: mock_exchange
    app.dependency_overrides[get_db] = lambda: mock_db
    
    try:
        response = client.post("/api/strategies/strat_123/activate")
        assert response.status_code == 422
        assert response.json()["message"]["error"] == "insufficient_funds"
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_activate_strategy_success(client, mock_db):
    """TASK-402: Verifica attivazione con successo ed esecuzione ordini."""
    mock_strategy = {
        "id": "strat_123",
        "title": "Test Strategy",
        "pair": "BTC/USDT",
        "timeframe": "1h",
        "params": {},
        "budget_eur": 100.0,
        "status": "APPROVED",
        "score": 0.5
    }
    
    # Mock per get_by_id
    exec_res_get = MagicMock()
    exec_res_get.data = mock_strategy
    mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = exec_res_get
    
    # Mock per update (status -> ACTIVE)
    exec_res_upd = MagicMock()
    exec_res_upd.data = [{"status": "ACTIVE"}]
    mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = exec_res_upd
    
    # Mock per insert (trade) - TUTTI i campi obbligatori di Trade
    exec_res_ins = MagicMock()
    exec_res_ins.data = [{
        "id": "trade_1",
        "strategy_id": "strat_123",
        "pair": "BTC/USDT",
        "action": "BUY",
        "status": "OPEN",
        "price": 50000.0,
        "quantity": 0.002
    }]
    mock_db.table.return_value.insert.return_value.execute.return_value = exec_res_ins
    
    mock_exchange = AsyncMock()
    mock_exchange.get_balance.return_value = 2000.0
    mock_exchange.get_ticker_price.return_value = 50000.0
    mock_exchange.get_holdings.return_value = {}
    mock_exchange.get_symbol_filters.return_value = {}
    mock_exchange.place_market_order.return_value = {"price": 50000.0, "quantity": 0.002}
    
    app.dependency_overrides[get_current_user] = lambda: "user"
    app.dependency_overrides[get_exchange] = lambda: mock_exchange
    app.dependency_overrides[get_db] = lambda: mock_db
    
    try:
        with patch("app.api.strategies.calculate_quantity", return_value=0.002):
            response = client.post("/api/strategies/strat_123/activate")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ACTIVE"
            assert len(data["allocation_trades"]) == 1
    finally:
        app.dependency_overrides.clear()
