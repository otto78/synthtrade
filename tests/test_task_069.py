import pytest
from app.services.stop_loss_service import StopLossService

def test_calculate_stop_loss():
    sl_service = StopLossService()
    # Long: 100 entry, 2% SL
    assert sl_service.calculate_price(100.0, "BUY", 0.02) == 98.0
    # Short: 100 entry, 2% SL
    assert sl_service.calculate_price(100.0, "SELL", 0.02) == 102.0

def test_check_hit():
    sl_service = StopLossService()
    # Long: SL 98, Price 97.9 -> Hit
    assert sl_service.is_hit(97.9, 98.0, "BUY") is True
    # Long: SL 98, Price 98.1 -> No Hit
    assert sl_service.is_hit(98.1, 98.0, "BUY") is False
    # Short: SL 102, Price 102.1 -> Hit
    assert sl_service.is_hit(102.1, 102.0, "SELL") is True
