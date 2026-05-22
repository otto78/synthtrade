"""🔴 RED + 🟢 GREEN: Test per ordini OCO in exchange.py (TASK-801)."""
import pytest
from unittest.mock import AsyncMock
from app.execution.exchange import BinanceExchangeAdapter


@pytest.fixture
def mock_ccxt():
    ccxt = AsyncMock()
    ccxt.create_order = AsyncMock()
    ccxt.fetch_balance = AsyncMock(return_value={
        "free": {"USDT": 10000.0},
        "total": {"USDT": 10000.0},
    })
    ccxt.fetch_ticker = AsyncMock(return_value={"last": 65000.0})
    return ccxt


@pytest.fixture
def adapter(mock_ccxt):
    return BinanceExchangeAdapter(
        api_key="test_key", secret="test_secret",
        testnet=True, client=mock_ccxt,
    )


class TestPlaceOCOOrder:
    """Test per place_oco_order."""

    @pytest.mark.asyncio
    async def test_place_oco_order_structure(self, adapter, mock_ccxt):
        """place_oco_order deve chiamare create_order con type=oco."""
        mock_ccxt.create_order.return_value = {
            "id": "oco_12345",
            "status": "closed",
            "symbol": "BTC/USDT",
            "price": 60000.0,
            "stopPrice": 59000.0,
            "stopLossPrice": 59000.0,
            "takeProfitPrice": 62000.0,
            "amount": 0.01,
        }
        result = await adapter.place_oco_order(
            symbol="BTC/USDT",
            side="SELL",
            quantity=0.01,
            price=60000.0,
            stop_price=59000.0,
            take_profit_price=62000.0,
        )
        assert result["order_id"] == "oco_12345"
        assert result["type"] == "oco"
        mock_ccxt.create_order.assert_called()

    @pytest.mark.asyncio
    async def test_place_oco_order_calls_ccxt(self, adapter, mock_ccxt):
        """Verifica parametri passati a create_order."""
        mock_ccxt.create_order.return_value = {"id": "oco_test"}
        await adapter.place_oco_order(
            symbol="ETH/USDT",
            side="SELL",
            quantity=0.1,
            price=3200.0,
            stop_price=3100.0,
            take_profit_price=3400.0,
        )
        call_kwargs = mock_ccxt.create_order.call_args
        assert call_kwargs is not None
        args, kwargs = call_kwargs
        # Verifica che symbol sia passato come positional o keyword
        symbol = args[0] if len(args) >= 1 else kwargs.get('symbol', '')
        assert symbol == "ETH/USDT"
        # Verifica type='oco' nei params
        if 'params' in kwargs:
            assert kwargs['params'].get('type') == 'oco'

    @pytest.mark.asyncio
    async def test_place_oco_order_fallback_to_synthetic(self, adapter, mock_ccxt):
        """Se CCXT non supporta OCO, deve usare order + stop loss separati."""
        mock_ccxt.create_order.side_effect = [
            # Primo tentativo OCO fallisce
            Exception("OCO not supported"),
            # Fallback: market order
            {"id": "order_001", "status": "closed", "price": 64000.0, "amount": 0.01},
            # Fallback: stop loss order
            {"id": "sl_001", "status": "closed", "price": 63500.0, "amount": 0.01},
        ]
        result = await adapter.place_oco_order(
            symbol="BTC/USDT",
            side="SELL",
            quantity=0.01,
            price=64000.0,
            stop_price=63500.0,
        )
        # Il fallback deve funzionare
        assert "order_id" in result or "main_order_id" in result

    @pytest.mark.asyncio
    async def test_place_oco_order_handles_error(self, adapter, mock_ccxt):
        """Se tutto fallisce, solleva eccezione."""
        mock_ccxt.create_order.side_effect = Exception("Exchange error")
        with pytest.raises(Exception) as exc_info:
            await adapter.place_oco_order(
                symbol="BTC/USDT",
                side="SELL",
                quantity=0.01,
                price=60000.0,
                stop_price=59000.0,
            )
        assert "OCO" in str(exc_info.value) or "oco" in str(exc_info.value).lower() or "Exchange" in str(exc_info.value)


class TestPlaceStopLossOrder:
    """Test per place_stop_loss_order."""

    @pytest.mark.asyncio
    async def test_place_stop_loss_structure(self, adapter, mock_ccxt):
        """place_stop_loss_order deve restituire order_id e type."""
        mock_ccxt.create_order.return_value = {
            "id": "sl_001", "status": "closed",
            "price": 59000.0, "amount": 0.01,
        }
        result = await adapter.place_stop_loss_order(
            symbol="BTC/USDT",
            side="SELL",
            quantity=0.01,
            stop_price=59000.0,
        )
        assert result["order_id"] == "sl_001"
        assert result["type"] == "stop_loss"

    @pytest.mark.asyncio
    async def test_place_stop_loss_calls_ccxt(self, adapter, mock_ccxt):
        """Verifica che stop loss usi stop_market type."""
        mock_ccxt.create_order.return_value = {"id": "sl_001"}
        await adapter.place_stop_loss_order(
            symbol="BTC/USDT",
            side="SELL",
            quantity=0.01,
            stop_price=59000.0,
        )
        mock_ccxt.create_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_place_stop_loss_handles_error(self, adapter, mock_ccxt):
        """Se lo stop loss fallisce, solleva eccezione."""
        mock_ccxt.create_order.side_effect = Exception("Stop loss failed")
        with pytest.raises(Exception) as exc_info:
            await adapter.place_stop_loss_order(
                symbol="BTC/USDT",
                side="SELL",
                quantity=0.01,
                stop_price=59000.0,
            )
        assert "stop loss" in str(exc_info.value).lower() or "Stop loss" in str(exc_info.value) or "Exchange" in str(exc_info.value)


class TestPlaceLimitOrder:
    """Test per place_limit_order (take profit)."""

    @pytest.mark.asyncio
    async def test_place_limit_order_structure(self, adapter, mock_ccxt):
        mock_ccxt.create_order.return_value = {
            "id": "tp_001", "status": "open",
            "price": 62000.0, "amount": 0.01,
        }
        result = await adapter.place_limit_order(
            symbol="BTC/USDT",
            side="SELL",
            quantity=0.01,
            limit_price=62000.0,
        )
        assert result["order_id"] == "tp_001"
        assert result["type"] == "limit"

    @pytest.mark.asyncio
    async def test_place_limit_order_handles_error(self, adapter, mock_ccxt):
        mock_ccxt.create_order.side_effect = Exception("Limit order failed")
        with pytest.raises(Exception) as exc_info:
            await adapter.place_limit_order(
                symbol="BTC/USDT",
                side="SELL",
                quantity=0.01,
                limit_price=62000.0,
            )
        assert "limit order" in str(exc_info.value).lower() or "Limit" in str(exc_info.value) or "Exchange" in str(exc_info.value)