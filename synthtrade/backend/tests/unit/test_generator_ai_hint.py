import pytest
from unittest.mock import AsyncMock, MagicMock
from app.execution.schemas import StrategyRequest
from app.ai.request_enricher import enrich_request_with_ai
from app.ai.model_client import AllModelsUnavailableError

@pytest.mark.asyncio
async def test_enrich_request_with_ai_empty_text():
    """
    TASK-044: se free_text è None o vuoto, enrich_request_with_ai() restituisce l'input invariato
    """
    req = StrategyRequest(
        budget_eur=100.0,
        duration_days=30,
        asset_class="crypto",
        risk_level="medium",
        free_text=None
    )
    result = await enrich_request_with_ai(req)
    assert result == req
    
    req.free_text = "   "
    result = await enrich_request_with_ai(req)
    assert result == req

@pytest.mark.asyncio
async def test_enrich_request_with_ai_success(monkeypatch):
    """
    TASK-043: enrich_request_with_ai(req) chiama il modello LLM con il free_text 
    e restituisce una lista di simboli suggeriti e un template preferito
    """
    req = StrategyRequest(
        budget_eur=100.0,
        duration_days=30,
        asset_class="crypto",
        risk_level="medium",
        free_text="Preferisco trend following su Bitcoin ed Ethereum"
    )
    
    mock_response = MagicMock()
    # Mock output JSON from AI
    mock_response.content = '{"symbols": ["BTC/USDT", "ETH/USDT"], "template": "trend_ema"}'
    
    mock_client = MagicMock()
    mock_client.call_with_fallback = AsyncMock(return_value=mock_response)
    
    # Mocking the creation of ModelClient or the function that uses it
    monkeypatch.setattr("app.ai.request_enricher.get_model_client", lambda: mock_client)
    
    result = await enrich_request_with_ai(req)
    
    assert "BTC/USDT" in result.symbols
    assert "ETH/USDT" in result.symbols
    # Nota: la logica esatta dipende da come implementiamo enrich_request_with_ai
    # Per ora verifichiamo che i simboli siano stati estratti

@pytest.mark.asyncio
async def test_enrich_request_with_ai_model_failure(monkeypatch):
    """
    TASK-045: se il modello non è disponibile, la funzione restituisce l'input invariato (graceful degradation)
    """
    req = StrategyRequest(
        budget_eur=100.0,
        duration_days=30,
        asset_class="crypto",
        risk_level="medium",
        free_text="Preferisco trend following su Bitcoin"
    )
    
    mock_client = MagicMock()
    mock_client.call_with_fallback = AsyncMock(side_effect=AllModelsUnavailableError("Down"))
    
    monkeypatch.setattr("app.ai.request_enricher.get_model_client", lambda: mock_client)
    
    result = await enrich_request_with_ai(req)
    assert result.symbols is None or result.symbols == [] # Depende dalla logica
