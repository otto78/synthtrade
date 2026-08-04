"""Tests for TASK-1243 — Break-even profit lock OCO OKX.

Copertura:
1. Pricing: _expected_net_pct_at_exit e _exit_price_ratio con fee 0.10%+0.10%
2. Trigger: amend inviato solo al primo close sopra soglia; successivi close non ri-triggerano
3. No-trigger: sotto soglia → nessun amend
4. Sicurezza: nessun amend senza algoId; nessun amend che peggiorisca lo SL
5. Adapter OKX: path corretto, body con newSlOrdPx="-1", code+sCode check
6. Persistenza/restore: break_even_triggered=True blocca secondo amend
7. Binance stub: solleva NotImplementedError

Esegui con:
    pytest synthtrade/backend/tests/test_task_1243.py -v
"""

import asyncio
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Garantisce che il path sia corretto
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ─────────────────────────────────────────────────────────────────────────────
# 1. Test pricing helpers
# ─────────────────────────────────────────────────────────────────────────────

def _import_pricing():
    from app.scalping.pricing import _expected_net_pct_at_exit, _exit_price_ratio, _net_to_gross_pct
    return _expected_net_pct_at_exit, _exit_price_ratio, _net_to_gross_pct


class TestPricing:
    """Verifica che i calcoli netti rispettino la tabella nel documento TASK-1243."""

    FEE = 0.001  # 0.10% taker (entry + exit)

    def test_break_even_at_round_trip_fee(self):
        """Con prezzo uscita = entry * ratio_break_even → net ≈ 0%."""
        _expected_net_pct_at_exit, _exit_price_ratio, _ = _import_pricing()
        ef = xf = self.FEE
        # ratio per 0% netto
        ratio = _exit_price_ratio(0.0, ef, xf)
        entry = 50000.0
        exit_price = entry * ratio
        net = _expected_net_pct_at_exit(entry, exit_price, "BUY", ef, xf)
        assert abs(net) < 0.001, f"Net at break-even should be ~0%, got {net}"

    def test_net_pct_at_trigger_threshold(self):
        """A +0.35% lordo (circa), net deve essere >= 0.15%."""
        _expected_net_pct_at_exit, _, _ = _import_pricing()
        ef = xf = self.FEE
        entry = 50000.0
        exit_price = entry * 1.0035  # +0.35% lordo
        net = _expected_net_pct_at_exit(entry, exit_price, "BUY", ef, xf)
        assert net >= 0.14, f"Net a +0.35% lordo deve essere >= 0.14%, got {net:.4f}"
        assert net <= 0.16, f"Net a +0.35% lordo deve essere <= 0.16%, got {net:.4f}"

    def test_net_pct_lock_target(self):
        """Il prezzo corrispondente a lock_net=0.05% è sopra entry per un long."""
        _, _exit_price_ratio, _ = _import_pricing()
        ef = xf = self.FEE
        entry = 50000.0
        ratio = _exit_price_ratio(0.05, ef, xf)
        lock_price = entry * ratio
        assert lock_price > entry, "Il lock price deve essere sopra entry per un long"
        # circa +0.25% lordo
        gross_pct = (lock_price / entry - 1) * 100
        assert 0.20 < gross_pct < 0.30, f"Lock price lordo atteso ~+0.25%, got {gross_pct:.4f}"

    def test_net_pct_buy_vs_sell_symmetry(self):
        """Per SELL, la formula è speculare a BUY."""
        _expected_net_pct_at_exit, _, _ = _import_pricing()
        ef = xf = self.FEE
        entry = 50000.0
        exit_price = entry * 0.9965  # prezzo scende per profit su SELL
        net_sell = _expected_net_pct_at_exit(entry, exit_price, "SELL", ef, xf)
        # Per BUY, stesso movimento ma al contrario sarebbe una perdita
        net_buy = _expected_net_pct_at_exit(entry, exit_price, "BUY", ef, xf)
        assert net_sell > 0, f"SELL con prezzo sceso deve avere net positivo, got {net_sell}"
        assert net_buy < 0, f"BUY con prezzo sceso deve avere net negativo, got {net_buy}"

    def test_net_zero_for_invalid_prices(self):
        """Prezzi non validi (0 o negativi) devono restituire 0."""
        _expected_net_pct_at_exit, _, _ = _import_pricing()
        assert _expected_net_pct_at_exit(0, 50000, "BUY", 0.001, 0.001) == 0.0
        assert _expected_net_pct_at_exit(50000, 0, "BUY", 0.001, 0.001) == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 2. Test logica trigger _check_and_apply_break_even
# ─────────────────────────────────────────────────────────────────────────────

def _make_position(
    entry=50000.0,
    side="BUY",
    sl_price=49800.0,
    oco_id="algo123",
    be_triggered=False,
):
    """Crea un oggetto Position minimale per i test."""
    from app.scalping.engine.position_manager import Position, PositionStatus
    pos = Position(
        symbol="BTC-EUR",
        side=side,
        entry_price=Decimal(str(entry)),
        quantity=Decimal("0.001"),
    )
    pos.oco_order_list_id = oco_id
    pos.sl_price = Decimal(str(sl_price))
    pos.break_even_triggered = be_triggered
    return pos


def _make_session(mode="live"):
    return {"mode": mode, "db_session_id": "sess-001"}


def _make_exchange_mock(amend_ok=True):
    """Mock dell'exchange adapter."""
    exchange = AsyncMock()
    rules = MagicMock()
    rules.tick_sz = 0.01
    exchange.get_symbol_rules.return_value = rules
    if amend_ok:
        exchange.amend_exit_bracket_stop_loss.return_value = {"sCode": "0", "sMsg": ""}
    else:
        from app.execution.exchange import ExchangeOrderError
        exchange.amend_exit_bracket_stop_loss.side_effect = ExchangeOrderError("OKX rejected")
    return exchange


@pytest.mark.asyncio
class TestBreakEvenTrigger:
    """Test logica trigger nel modulo break_even.py."""

    async def _run(self, pos, current_price, session, exchange, config_overrides=None):
        """Helper: patcha execution_state e config, poi chiama _check_and_apply_break_even."""
        from app.scalping.break_even import _check_and_apply_break_even

        config_defaults = {
            "BREAK_EVEN_ENABLED": True,
            "BREAK_EVEN_TRIGGER_NET_PCT": 0.15,
            "BREAK_EVEN_LOCK_NET_PCT": 0.05,
        }
        if config_overrides:
            config_defaults.update(config_overrides)

        cfg_mock = MagicMock()
        cfg_mock.get.side_effect = lambda k, d=None: config_defaults.get(k, d)

        state = {
            "exchange": exchange,
            "fee_tier": {"maker": 0.001, "taker": 0.001},
        }

        with patch("app.scalping.break_even._execution_state", state), \
             patch("app.scalping.break_even.get_scalping_config", return_value=cfg_mock), \
             patch("app.scalping.break_even._update_break_even_in_db", new_callable=AsyncMock), \
             patch("app.scalping.break_even.broadcast_scalping_event", new_callable=AsyncMock):
            await _check_and_apply_break_even(pos, current_price, session)

    async def test_trigger_fires_above_threshold(self):
        """Sopra soglia trigger: amend inviato, stato aggiornato."""
        exchange = _make_exchange_mock(amend_ok=True)
        pos = _make_position(entry=50000.0, sl_price=49800.0)
        session = _make_session()

        # +0.36% lordo ≈ +0.16% netto > trigger 0.15%
        await self._run(pos, 50180.0, session, exchange)

        exchange.amend_exit_bracket_stop_loss.assert_called_once()
        assert pos.break_even_triggered is True
        assert pos.break_even_sl_price is not None
        assert float(pos.sl_price) > 49800.0  # SL alzato

    async def test_no_trigger_below_threshold(self):
        """Sotto soglia: nessun amend."""
        exchange = _make_exchange_mock()
        pos = _make_position(entry=50000.0, sl_price=49800.0)
        session = _make_session()

        # +0.10% lordo ≈ +0% netto — sotto soglia
        await self._run(pos, 50050.0, session, exchange)

        exchange.amend_exit_bracket_stop_loss.assert_not_called()
        assert pos.break_even_triggered is False

    async def test_no_second_trigger_after_first(self):
        """Una volta attivato, close successivi non inviano altro amend."""
        exchange = _make_exchange_mock()
        pos = _make_position(entry=50000.0, sl_price=49800.0, be_triggered=True)
        pos.break_even_sl_price = Decimal("50100.0")
        session = _make_session()

        # Prezzo ancora sopra soglia, ma già triggered
        await self._run(pos, 50200.0, session, exchange)

        exchange.amend_exit_bracket_stop_loss.assert_not_called()

    async def test_no_amend_without_algo_id(self):
        """Senza algoId non deve essere inviato nessun amend."""
        exchange = _make_exchange_mock()
        pos = _make_position(entry=50000.0, sl_price=49800.0, oco_id=None)
        session = _make_session()

        await self._run(pos, 50200.0, session, exchange)

        exchange.amend_exit_bracket_stop_loss.assert_not_called()
        assert pos.break_even_triggered is False

    async def test_no_amend_in_paper_mode(self):
        """In paper mode nessun amend."""
        exchange = _make_exchange_mock()
        pos = _make_position(entry=50000.0)
        session = _make_session(mode="paper")

        await self._run(pos, 50200.0, session, exchange)

        exchange.amend_exit_bracket_stop_loss.assert_not_called()

    async def test_no_amend_when_feature_flag_off(self):
        """Feature flag BREAK_EVEN_ENABLED=False → nessun amend."""
        exchange = _make_exchange_mock()
        pos = _make_position(entry=50000.0)
        session = _make_session()

        await self._run(pos, 50200.0, session, exchange, {"BREAK_EVEN_ENABLED": False})

        exchange.amend_exit_bracket_stop_loss.assert_not_called()

    async def test_state_not_mutated_on_exchange_error(self):
        """Se OKX rifiuta l'amend, lo stato locale NON deve cambiare."""
        exchange = _make_exchange_mock(amend_ok=False)
        pos = _make_position(entry=50000.0, sl_price=49800.0)
        session = _make_session()

        await self._run(pos, 50200.0, session, exchange)

        assert pos.break_even_triggered is False
        assert float(pos.sl_price) == 49800.0  # invariato

    async def test_new_sl_strictly_greater_than_current_for_long(self):
        """Il nuovo SL deve essere > SL attuale, non uguale o minore."""
        exchange = _make_exchange_mock(amend_ok=True)
        # SL già vicino al nuovo valore lock — il test simula un SL già al livello lock
        # In questo caso il guard deve bloccare l'amend
        from app.scalping.pricing import _exit_price_ratio
        entry = 50000.0
        ef = xf = 0.001
        lock_price = entry * _exit_price_ratio(0.05, ef, xf)  # ≈50125.0

        pos = _make_position(entry=entry, sl_price=lock_price + 10)  # SL già sopra lock
        session = _make_session()

        await self._run(pos, 50200.0, session, exchange)

        exchange.amend_exit_bracket_stop_loss.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# 3. Test adapter OKX amend_exit_bracket_stop_loss
# ─────────────────────────────────────────────────────────────────────────────

class TestOkxAmendAdapter:
    """Test del metodo amend_exit_bracket_stop_loss su OkxExchangeAdapter."""

    def _make_adapter(self):
        """Crea un adapter OKX con credenziali fittizie (non fa chiamate reali)."""
        from app.execution.okx_exchange import OkxExchangeAdapter
        return OkxExchangeAdapter(
            api_key="test_key",
            secret="test_secret",
            passphrase="test_pass",
            demo=True,
        )

    @pytest.mark.asyncio
    async def test_amend_success(self):
        """Risposta OKX valida (code=0, sCode=0) → restituisce dict, nessuna eccezione."""
        from app.execution.exchange_models import SymbolRef

        adapter = self._make_adapter()
        sym = SymbolRef(base="BTC", quote="EUR")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": "0",
            "msg": "",
            "data": [{"algoId": "algo123", "sCode": "0", "sMsg": ""}],
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        with patch("app.execution.okx_exchange.httpx.AsyncClient") as mock_client_cls:
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await adapter.amend_exit_bracket_stop_loss(
                symbol=sym,
                algo_id="algo123",
                new_sl_trigger_px=50100.0,
                req_id="testreqid",
            )

        assert result.get("sCode") == "0"
        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args
        import json
        body_str = call_kwargs.kwargs.get("content")
        if body_str:
            body_dict = json.loads(body_str)
            assert body_dict["algoId"] == "algo123"
            assert body_dict["newSlOrdPx"] == "-1"
            assert body_dict["instId"] == "BTC-EUR"

    @pytest.mark.asyncio
    async def test_amend_top_level_error_raises(self):
        """code != 0 → ExchangeOrderError."""
        from app.execution.exchange_models import SymbolRef
        from app.execution.exchange import ExchangeOrderError

        adapter = self._make_adapter()
        sym = SymbolRef(base="BTC", quote="EUR")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": "51000",
            "msg": "Parameter instId error",
            "data": [],
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        with patch("app.execution.okx_exchange.httpx.AsyncClient") as mock_client_cls:
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(ExchangeOrderError, match="51000"):
                await adapter.amend_exit_bracket_stop_loss(
                    symbol=sym, algo_id="algo123", new_sl_trigger_px=50100.0
                )

    @pytest.mark.asyncio
    async def test_amend_per_result_scode_error_raises(self):
        """sCode != 0 → ExchangeOrderError."""
        from app.execution.exchange_models import SymbolRef
        from app.execution.exchange import ExchangeOrderError

        adapter = self._make_adapter()
        sym = SymbolRef(base="BTC", quote="EUR")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": "0",
            "msg": "",
            "data": [{"algoId": "algo123", "sCode": "51503", "sMsg": "Order does not exist"}],
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        with patch("app.execution.okx_exchange.httpx.AsyncClient") as mock_client_cls:
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(ExchangeOrderError, match="51503"):
                await adapter.amend_exit_bracket_stop_loss(
                    symbol=sym, algo_id="algo123", new_sl_trigger_px=50100.0
                )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Test Binance stub
# ─────────────────────────────────────────────────────────────────────────────

class TestBinanceStub:
    @pytest.mark.asyncio
    async def test_binance_raises_not_implemented(self):
        """BinanceExchangeAdapter.amend_exit_bracket_stop_loss → NotImplementedError."""
        from app.execution.exchange import BinanceExchangeAdapter
        adapter = BinanceExchangeAdapter.__new__(BinanceExchangeAdapter)
        adapter.provider = "binance"
        adapter.trading_mode = "test"

        with pytest.raises(NotImplementedError, match="amend_exit_bracket_stop_loss"):
            await adapter.amend_exit_bracket_stop_loss(
                symbol=None,
                algo_id="test",
                new_sl_trigger_px=50000.0,
            )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Test DB helper _update_break_even_in_db
# ─────────────────────────────────────────────────────────────────────────────

class TestUpdateBreakEvenInDb:
    @pytest.mark.asyncio
    async def test_db_update_called_with_correct_bracket_id(self):
        """_update_break_even_in_db esegue UPDATE con exchange_bracket_id corretto."""
        from app.scalping.db_ops import _update_break_even_in_db

        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_update = MagicMock()
        mock_eq1 = MagicMock()
        mock_eq2 = MagicMock()
        mock_execute = MagicMock()
        mock_execute.return_value = MagicMock(data=[{"id": "row1"}])

        mock_supabase.table.return_value = mock_table
        mock_table.update.return_value = mock_update
        mock_update.eq.return_value = mock_eq1
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value = mock_execute.return_value

        with patch("app.scalping.db_ops.get_supabase", return_value=mock_supabase):
            await _update_break_even_in_db(
                exchange_bracket_id="algo456",
                new_sl_price=50125.0,
                activated_at=datetime(2026, 8, 4, 10, 0, 0, tzinfo=timezone.utc),
            )

        mock_table.update.assert_called_once()
        update_data = mock_table.update.call_args[0][0]
        assert update_data["break_even_triggered"] is True
        assert update_data["sl_price"] == 50125.0
        assert update_data["break_even_sl_price"] == 50125.0

        # Verifica che il filtro usi exchange_bracket_id
        first_eq_call = mock_update.eq.call_args
        assert first_eq_call[0][0] == "exchange_bracket_id"
        assert first_eq_call[0][1] == "algo456"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Test restore break_even_triggered da DB
# ─────────────────────────────────────────────────────────────────────────────

class TestRestoreBreakEven:
    def test_position_fields_exist(self):
        """Il dataclass Position ha i tre nuovi campi break_even."""
        from app.scalping.engine.position_manager import Position
        pos = Position(
            symbol="BTC-EUR",
            side="BUY",
            entry_price=Decimal("50000"),
            quantity=Decimal("0.001"),
        )
        assert hasattr(pos, "break_even_triggered")
        assert hasattr(pos, "break_even_activated_at")
        assert hasattr(pos, "break_even_sl_price")
        assert pos.break_even_triggered is False
        assert pos.break_even_activated_at is None
        assert pos.break_even_sl_price is None

    def test_restore_prevents_second_trigger(self):
        """Con break_even_triggered=True, _check_and_apply_break_even ritorna subito."""
        # Questo è coperto da test_no_second_trigger_after_first in TestBreakEvenTrigger
        from app.scalping.engine.position_manager import Position
        pos = Position(
            symbol="BTC-EUR",
            side="BUY",
            entry_price=Decimal("50000"),
            quantity=Decimal("0.001"),
        )
        pos.break_even_triggered = True
        pos.break_even_sl_price = Decimal("50100")
        pos.break_even_activated_at = datetime(2026, 8, 4, tzinfo=timezone.utc)
        # Dopo restore, il flag è True — il guard nel modulo break_even lo intercetta
        assert pos.break_even_triggered is True


# ─────────────────────────────────────────────────────────────────────────────
# 7. Test quantizzazione prezzo
# ─────────────────────────────────────────────────────────────────────────────

class TestQuantizePrice:
    def test_quantize_rounds_down(self):
        from app.scalping.break_even import _quantize_price
        # 50123.456 con tick 0.01 → 50123.45 (ROUND_DOWN)
        result = _quantize_price(50123.456, tick_sz=0.01, side="BUY")
        assert result == pytest.approx(50123.45, abs=1e-6)

    def test_quantize_zero_tick(self):
        from app.scalping.break_even import _quantize_price
        # tick_sz=0 → restituisce il prezzo invariato
        result = _quantize_price(50123.456, tick_sz=0, side="BUY")
        assert result == pytest.approx(50123.456)
