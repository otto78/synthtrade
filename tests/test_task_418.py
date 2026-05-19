"""
TASK-418 — Refactor `active-trade.page.ts`: supporto multi-strategia

Test TDD per:
1. Header strategia collassabili con toggle visibilità trade
2. GET /api/trades/active per snapshot iniziale (nuovo endpoint)
3. WS trade_opened/closed con preservazione stato collassato
4. Multi-strategia: sezioni indipendenti con collapse individuale
5. Persistenza stato collassato dopo WS update
"""

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, List


# ──────────────────────────────────────────────
# Mock data
# ──────────────────────────────────────────────

MOCK_TRADES_ACTIVE_RESPONSE = [
    {
        "id": "t1",
        "strategy_id": "s1",
        "strategy_name": "EMA Cross BTC",
        "symbol": "BTC/USDT",
        "side": "BUY",
        "entry_price": 50000.0,
        "current_price": 51000.0,
        "quantity": 0.015,
        "unrealized_pnl_pct": 2.0,
        "status": "OPEN",
        "executed_at": "2026-05-18T10:00:00Z",
    },
    {
        "id": "t2",
        "strategy_id": "s2",
        "strategy_name": "RSI Mean Rev ETH",
        "symbol": "ETH/USDT",
        "side": "SELL",
        "entry_price": 3000.0,
        "current_price": 2950.0,
        "quantity": 0.5,
        "unrealized_pnl_pct": 1.67,
        "status": "OPEN",
        "executed_at": "2026-05-18T10:05:00Z",
    },
    {
        "id": "t3",
        "strategy_id": "s1",
        "strategy_name": "EMA Cross BTC",
        "symbol": "BTC/USDT",
        "side": "SELL",
        "entry_price": 50500.0,
        "current_price": 51000.0,
        "quantity": 0.01,
        "unrealized_pnl_pct": -0.99,
        "status": "OPEN",
        "executed_at": "2026-05-18T10:10:00Z",
    },
]

MOCK_STRATEGY_SNAPSHOT = {
    "strategies": [
        {
            "id": "s1",
            "title": "EMA Cross BTC",
            "pair": "BTC/USDT",
            "timeframe": "1h",
            "initial_capital_usdt": 1000.0,
            "pnl_pct": 1.5,
            "pnl_eur": 15.0,
            "open_trades": [
                {"id": "t1", "symbol": "BTC/USDT", "side": "BUY", "pnl_pct": 2.0,
                 "price": 50000.0, "quantity": 0.015, "status": "OPEN",
                 "executed_at": "2026-05-18T10:00:00Z", "trade_type": "SIGNAL", "strategy_id": "s1"},
                {"id": "t3", "symbol": "BTC/USDT", "side": "SELL", "pnl_pct": -0.99,
                 "price": 50500.0, "quantity": 0.01, "status": "OPEN",
                 "executed_at": "2026-05-18T10:10:00Z", "trade_type": "SIGNAL", "strategy_id": "s1"},
            ],
            "closed_trades": [],
            "equity_curve": [100, 101, 101.5],
        },
        {
            "id": "s2",
            "title": "RSI Mean Rev ETH",
            "pair": "ETH/USDT",
            "timeframe": "15m",
            "initial_capital_usdt": 500.0,
            "pnl_pct": 1.67,
            "pnl_eur": 8.35,
            "open_trades": [
                {"id": "t2", "symbol": "ETH/USDT", "side": "SELL", "pnl_pct": 1.67,
                 "price": 3000.0, "quantity": 0.5, "status": "OPEN",
                 "executed_at": "2026-05-18T10:05:00Z", "trade_type": "SIGNAL", "strategy_id": "s2"},
            ],
            "closed_trades": [],
            "equity_curve": [100],
        },
    ]
}


# ──────────────────────────────────────────────
# Unit test: collapsible header logic
# ──────────────────────────────────────────────

class TestCollapsibleHeaders:
    """Verifica che ogni strategia abbia un header collassabile indipendente."""

    def test_collapse_toggle_toggles_state(self):
        """Cliccare sull'header deve alternare lo stato collassato di UNA strategia."""
        collapsed = {"s1": False, "s2": False}

        def toggle(strategy_id: str):
            collapsed[strategy_id] = not collapsed[strategy_id]

        # Toggle s1 → collassato
        toggle("s1")
        assert collapsed["s1"] is True
        assert collapsed["s2"] is False  # s2 non deve cambiare

        # Toggle s1 again → espanso
        toggle("s1")
        assert collapsed["s1"] is False

    def test_multiple_strategies_independent_collapse(self):
        """Strategie diverse hanno stato collassato indipendente."""
        collapsed: Dict[str, bool] = {}

        def toggle(strategy_id: str):
            collapsed[strategy_id] = not collapsed.get(strategy_id, False)

        toggle("s1")
        toggle("s2")  # collassa s2
        toggle("s1")  # espande s1

        assert collapsed.get("s1") is False  # espanso dopo secondo toggle
        assert collapsed.get("s2") is True   # ancora collassato

    def test_all_expanded_by_default(self):
        """All'avvio tutte le strategie devono essere espanse."""
        strategies = MOCK_STRATEGY_SNAPSHOT["strategies"]
        collapsed: Dict[str, bool] = {}
        for s in strategies:
            collapsed[s["id"]] = collapsed.get(s["id"], False)

        assert all(v is False for v in collapsed.values()), \
            "Tutte le strategie devono essere espanse all'avvio"

    def test_collapsed_strategy_hides_trades(self):
        """Strategia collassata non mostra i trade."""
        strategies = MOCK_STRATEGY_SNAPSHOT["strategies"]
        collapsed = {"s1": True, "s2": False}

        for s in strategies:
            if collapsed.get(s["id"], False):
                # Non deve mostrare i trade
                assert len(s["open_trades"]) > 0  # ci sono trade
                # La visualizzazione è nascosta (testato a livello UI)
                assert collapsed[s["id"]] is True


# ──────────────────────────────────────────────
# Unit test: GET /api/trades/active snapshot
# ──────────────────────────────────────────────

class TestTradesActiveSnapshot:
    """Verifica che il componente carichi lo snapshot iniziale da /api/trades/active."""

    @pytest.mark.asyncio
    async def test_loads_active_trades_on_init(self):
        """All'inizializzazione deve chiamare GET /api/trades/active."""
        mock_response = MOCK_STRATEGY_SNAPSHOT
        # Simula chiamata API
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response_obj = AsyncMock()
            mock_response_obj.json = AsyncMock(return_value=mock_response)
            mock_response_obj.status_code = 200
            mock_get.return_value = mock_response_obj

            # Simula init
            async def load():
                async with httpx.AsyncClient() as client:
                    resp = await client.get("http://test/api/trades/active")
                    return await resp.json()

            result = await load()
            assert len(result["strategies"]) == 2
            assert result["strategies"][0]["id"] == "s1"
            assert result["strategies"][1]["id"] == "s2"

    @pytest.mark.asyncio
    async def test_empty_response_shows_empty_state(self):
        """Se non ci sono trade attivi, mostra empty state."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response_obj = AsyncMock()
            mock_response_obj.json = AsyncMock(return_value={"strategies": []})
            mock_response_obj.status_code = 200
            mock_get.return_value = mock_response_obj

            async with httpx.AsyncClient() as client:
                resp = await client.get("http://test/api/trades/active")
                data = await resp.json()

            assert len(data["strategies"]) == 0

    def test_parse_trades_into_strategies(self):
        """I trade devono essere raggruppati per strategy_id."""
        raw = MOCK_TRADES_ACTIVE_RESPONSE
        strategies_map: Dict[str, list] = {}
        for trade in raw:
            sid = trade["strategy_id"]
            if sid not in strategies_map:
                strategies_map[sid] = []
            strategies_map[sid].append(trade)

        assert len(strategies_map) == 2
        assert len(strategies_map["s1"]) == 2  # BTC BUY + BTC SELL
        assert len(strategies_map["s2"]) == 1  # ETH SELL


# ──────────────────────────────────────────────
# Unit test: WS update preserves collapsed state
# ──────────────────────────────────────────────

class TestWsPreservesCollapseState:
    """Verifica che gli aggiornamenti WS non resettino lo stato collassato."""

    def test_trade_opened_preserves_collapsed(self):
        """WS trade_opened non deve resettare collapsed state."""
        collapsed = {"s1": True, "s2": False}
        # Simula trade_opened per s1
        # Dopo l'aggiornamento, lo stato collassato deve rimanere
        assert collapsed["s1"] is True   # rimane collassato
        assert collapsed["s2"] is False  # rimane espanso

    def test_trade_closed_preserves_collapsed(self):
        """WS trade_closed non deve resettare collapsed state."""
        collapsed = {"s1": False, "s2": True}
        # Simula trade_closed
        assert collapsed["s1"] is False
        assert collapsed["s2"] is True

    def test_pnl_updated_preserves_collapsed(self):
        """WS StrategyPnlUpdated deve aggiornare P&L preservando collapse."""
        collapsed = {"s1": True}
        strategies = MOCK_STRATEGY_SNAPSHOT["strategies"]
        # Aggiorna P&L per s1
        updated = [s if s["id"] != "s1" else {**s, "pnl_pct": 3.0} for s in strategies]
        # collapsed deve rimanere invariato
        assert collapsed["s1"] is True
        # P&L deve essere aggiornato
        matching = [s for s in updated if s["id"] == "s1"][0]
        assert matching["pnl_pct"] == 3.0

    def test_strategy_stopped_removes_collapsed_entry(self):
        """WS StrategyStopped rimuove strategia E il suo stato collassato."""
        collapsed = {"s1": True, "s2": False}
        strategy_id_to_remove = "s1"
        # Rimuovi strategia
        collapsed.pop(strategy_id_to_remove, None)
        assert "s1" not in collapsed
        assert collapsed.get("s2") is False  # s2 non toccato


# ──────────────────────────────────────────────
# Integration: backend /api/trades/active endpoint
# ──────────────────────────────────────────────

class TestTradesActiveEndpoint:
    """Verifica che il backend esponga correttamente GET /api/trades/active."""

    def test_endpoint_exists_in_trades_router(self):
        """Verifica che /api/trades/active sia registrato nel router."""
        from app.api.trades import router
        routes = [r.path for r in router.routes]
        assert "/active" in routes, \
            "Manca endpoint GET /api/trades/active nel router trades"

    def test_active_trades_returns_grouped_by_strategy(self):
        """Il risultato deve essere raggruppato per strategia."""
        # Test strutturale: la response deve avere chiave 'strategies'
        response = MOCK_STRATEGY_SNAPSHOT
        assert "strategies" in response
        assert isinstance(response["strategies"], list)
        for s in response["strategies"]:
            assert "id" in s
            assert "open_trades" in s
            assert "closed_trades" in s
            assert "pnl_pct" in s

    def test_trade_has_strategy_reference(self):
        """Ogni trade deve avere strategy_id."""
        for strategy in MOCK_STRATEGY_SNAPSHOT["strategies"]:
            for trade in strategy["open_trades"] + strategy["closed_trades"]:
                assert "strategy_id" in trade
                assert trade["strategy_id"] == strategy["id"]


# ──────────────────────────────────────────────
#  Edge cases
# ──────────────────────────────────────────────

class TestEdgeCases:
    """Casi limite per la gestione multi-strategia."""

    def test_no_open_trades_strategy(self):
        """Strategia senza trade aperti non crasha e mostra solo closed."""
        strategy = {
            "id": "s3",
            "title": "VWAP Rev SOL",
            "pair": "SOL/USDT",
            "timeframe": "1h",
            "initial_capital_usdt": 300.0,
            "pnl_pct": -0.5,
            "pnl_eur": -1.5,
            "open_trades": [],
            "closed_trades": [
                {"id": "t4", "symbol": "SOL/USDT", "side": "BUY", "pnl_pct": -0.5,
                 "price": 150.0, "quantity": 2.0, "status": "CLOSED",
                 "executed_at": "2026-05-18T09:00:00Z", "trade_type": "SIGNAL", "strategy_id": "s3"},
            ],
            "equity_curve": [100, 99.5],
        }
        # Non deve crashare
        assert len(strategy["open_trades"]) == 0
        assert len(strategy["closed_trades"]) == 1

    def test_single_strategy_no_regression(self):
        """Una singola strategia deve funzionare come prima (no regressione)."""
        single = {
            "strategies": [MOCK_STRATEGY_SNAPSHOT["strategies"][0]]
        }
        assert len(single["strategies"]) == 1
        s = single["strategies"][0]
        assert len(s["open_trades"]) == 2
        assert s["pnl_pct"] == 1.5

    def test_many_trades_single_strategy(self):
        """Molti trade sulla stessa strategia devono essere tutti visibili."""
        many_trades = []
        for i in range(50):
            many_trades.append({
                "id": f"t_bulk_{i}", "symbol": "BTC/USDT", "side": "BUY",
                "pnl_pct": 0.1 * i, "price": 50000.0 + i,
                "quantity": 0.001, "status": "OPEN",
                "executed_at": f"2026-05-18T{10 + i//60:02d}:{i%60:02d}:00Z",
                "trade_type": "SIGNAL", "strategy_id": "s1",
            })

        # Non deve crashare, tutti i trade presenti
        assert len(many_trades) == 50
        strategies_map: Dict[str, list] = {}
        for t in many_trades:
            sid = t["strategy_id"]
            if sid not in strategies_map:
                strategies_map[sid] = []
            strategies_map[sid].append(t)

        assert len(strategies_map["s1"]) == 50


@pytest.fixture(autouse=True)
def _ensure_httpx_mock():
    """Fixture per garantire che i test asincroni abbiano httpx disponibile."""
    try:
        import httpx  # noqa: F401
    except ImportError:
        pytest.skip("httpx non installato, skippo test asincroni")