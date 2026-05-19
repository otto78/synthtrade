"""
TASK-427: Frontend: selezione multi-crypto nel form generazione
TDD Red Phase - Test Suite

Requirements:
- Form con aggiunta di più crypto e slider percentuale
- Validazione: somma delle percentuali = 100%
- Supporto per allocation multi-crypto nel backend
"""
import pytest
from pydantic import ValidationError
from synthtrade.backend.app.execution.schemas import AllocationItem, StrategyRequest


def test_allocation_item_validation():
    """Test che AllocationItem valida correttamente symbol e percentage"""
    # Valid allocation
    item = AllocationItem(symbol="BTCUSDT", percentage=50.0)
    assert item.symbol == "BTCUSDT"
    assert item.percentage == 50.0

    # Invalid percentage < 0
    with pytest.raises(ValidationError):
        AllocationItem(symbol="ETHUSDT", percentage=-10.0)

    # Invalid percentage > 100
    with pytest.raises(ValidationError):
        AllocationItem(symbol="ETHUSDT", percentage=150.0)

    # Invalid empty symbol
    with pytest.raises(ValidationError):
        AllocationItem(symbol="", percentage=50.0)


def test_strategy_request_with_allocation():
    """Test che StrategyRequest accetta campo allocation"""
    request_data = {
        "budget_eur": 1000.0,
        "duration_days": 30,
        "risk_level": "medium",
        "asset_class": "crypto",
        "allocation": [
            {"symbol": "BTCUSDT", "percentage": 60.0},
            {"symbol": "ETHUSDT", "percentage": 40.0}
        ]
    }

    request = StrategyRequest(**request_data)
    assert len(request.allocation) == 2
    assert request.allocation[0].symbol == "BTCUSDT"
    assert request.allocation[0].percentage == 60.0
    assert request.allocation[1].symbol == "ETHUSDT"
    assert request.allocation[1].percentage == 40.0


def test_strategy_request_allocation_sum_validation():
    """Test che la somma delle percentuali deve essere 100%"""
    # Valid: sum = 100
    valid_data = {
        "budget_eur": 1000.0,
        "duration_days": 30,
        "risk_level": "medium",
        "asset_class": "crypto",
        "allocation": [
            {"symbol": "BTCUSDT", "percentage": 50.0},
            {"symbol": "ETHUSDT", "percentage": 30.0},
            {"symbol": "SOLUSDT", "percentage": 20.0}
        ]
    }
    request = StrategyRequest(**valid_data)
    assert sum(item.percentage for item in request.allocation) == 100.0

    # Invalid: sum != 100
    invalid_data = {
        "budget_eur": 1000.0,
        "duration_days": 30,
        "risk_level": "medium",
        "asset_class": "crypto",
        "allocation": [
            {"symbol": "BTCUSDT", "percentage": 60.0},
            {"symbol": "ETHUSDT", "percentage": 30.0}  # sum = 90, not 100
        ]
    }
    with pytest.raises(ValidationError, match="must sum to 100"):
        StrategyRequest(**invalid_data)


def test_strategy_request_allocation_optional():
    """Test che allocation è opzionale (backward compatibility con symbols)"""
    # Request senza allocation (usa symbols come prima)
    request_data = {
        "budget_eur": 1000.0,
        "duration_days": 30,
        "risk_level": "medium",
        "asset_class": "crypto",
        "symbols": ["BTCUSDT", "ETHUSDT"]
    }

    request = StrategyRequest(**request_data)
    assert request.symbols == ["BTCUSDT", "ETHUSDT"]
    assert request.allocation == []  # default empty list


def test_strategy_request_cannot_have_both_symbols_and_allocation():
    """Test che non si possono specificare sia symbols che allocation"""
    invalid_data = {
        "budget_eur": 1000.0,
        "duration_days": 30,
        "risk_level": "medium",
        "asset_class": "crypto",
        "symbols": ["BTCUSDT"],
        "allocation": [
            {"symbol": "ETHUSDT", "percentage": 100.0}
        ]
    }

    with pytest.raises(ValidationError, match="Cannot specify both 'symbols' and 'allocation'"):
        StrategyRequest(**invalid_data)


def test_allocation_item_symbol_format():
    """Test che i simboli devono essere uppercase e formato corretto"""
    # Valid uppercase
    item = AllocationItem(symbol="BTCUSDT", percentage=50.0)
    assert item.symbol == "BTCUSDT"

    # Lowercase should be converted to uppercase
    item = AllocationItem(symbol="ethusdt", percentage=50.0)
    assert item.symbol == "ETHUSDT"

    # Invalid format (too short)
    with pytest.raises(ValidationError):
        AllocationItem(symbol="BTC", percentage=50.0)


def test_allocation_empty_is_valid():
    """Test che allocation vuota è valida (backward compatibility)"""
    valid_data = {
        "budget_eur": 1000.0,
        "duration_days": 30,
        "risk_level": "medium",
        "asset_class": "crypto",
        "allocation": []  # Empty allocation is OK (falls back to AI selection)
    }

    request = StrategyRequest(**valid_data)
    assert request.allocation == []


def test_allocation_unique_symbols():
    """Test che i simboli in allocation devono essere unici"""
    invalid_data = {
        "budget_eur": 1000.0,
        "duration_days": 30,
        "risk_level": "medium",
        "asset_class": "crypto",
        "allocation": [
            {"symbol": "BTCUSDT", "percentage": 50.0},
            {"symbol": "BTCUSDT", "percentage": 50.0}  # Duplicate
        ]
    }

    with pytest.raises(ValidationError, match="Duplicate symbols in allocation"):
        StrategyRequest(**invalid_data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
