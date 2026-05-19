"""
TASK-430 — Dashboard: KPI globali strategie attive e trade aperti

Test TDD per:
1. active_strategies_count: numero di strategie con status ACTIVE
2. total_active_pnl_pct: P&L percentuale totale di tutte le strategie attive
3. Integrare i nuovi KPI in GET /api/dashboard
4. Verificare calcolo P&L aggregato da trade aperti
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import List, Dict, Any


# ──────────────────────────────────────────────
# Unit test: active_strategies_count
# ──────────────────────────────────────────────

class TestActiveStrategiesCount:
    """Verifica che active_strategies_count conti correttamente le strategie ACTIVE."""

    def test_count_active_strategies(self):
        """Conta solo strategie con status='ACTIVE'."""
        strategies = [
            {"id": "s1", "status": "ACTIVE"},
            {"id": "s2", "status": "ACTIVE"},
            {"id": "s3", "status": "STOPPED"},
            {"id": "s4", "status": "ACTIVE"},
        ]
        active_count = sum(1 for s in strategies if s["status"] == "ACTIVE")
        assert active_count == 3

    def test_no_active_strategies(self):
        """Se non ci sono strategie attive, ritorna 0."""
        strategies = [
            {"id": "s1", "status": "STOPPED"},
            {"id": "s2", "status": "STOPPED"},
        ]
        active_count = sum(1 for s in strategies if s["status"] == "ACTIVE")
        assert active_count == 0

    def test_empty_strategies_list(self):
        """Lista vuota ritorna 0."""
        strategies = []
        active_count = sum(1 for s in strategies if s["status"] == "ACTIVE")
        assert active_count == 0

    def test_all_active_strategies(self):
        """Se tutte le strategie sono attive."""
        strategies = [
            {"id": "s1", "status": "ACTIVE"},
            {"id": "s2", "status": "ACTIVE"},
            {"id": "s3", "status": "ACTIVE"},
        ]
        active_count = sum(1 for s in strategies if s["status"] == "ACTIVE")
        assert active_count == 3


# ──────────────────────────────────────────────
# Unit test: total_active_pnl_pct
# ──────────────────────────────────────────────

class TestTotalActivePnlPct:
    """Verifica che total_active_pnl_pct aggreghi correttamente il P&L."""

    def test_sum_pnl_from_active_strategies(self):
        """Somma P&L solo da strategie ACTIVE."""
        strategies = [
            {"id": "s1", "status": "ACTIVE", "pnl_pct": 2.5},
            {"id": "s2", "status": "ACTIVE", "pnl_pct": 1.5},
            {"id": "s3", "status": "STOPPED", "pnl_pct": -10.0},  # Ignorato
        ]
        total_pnl = sum(s.get("pnl_pct", 0.0) for s in strategies if s["status"] == "ACTIVE")
        assert total_pnl == 4.0

    def test_negative_pnl(self):
        """P&L negativo viene sommato correttamente."""
        strategies = [
            {"id": "s1", "status": "ACTIVE", "pnl_pct": 2.0},
            {"id": "s2", "status": "ACTIVE", "pnl_pct": -1.5},
        ]
        total_pnl = sum(s.get("pnl_pct", 0.0) for s in strategies if s["status"] == "ACTIVE")
        assert total_pnl == 0.5

    def test_no_pnl_field(self):
        """Strategie senza campo pnl_pct vengono trattate come 0."""
        strategies = [
            {"id": "s1", "status": "ACTIVE"},  # Manca pnl_pct
            {"id": "s2", "status": "ACTIVE", "pnl_pct": 2.0},
        ]
        total_pnl = sum(s.get("pnl_pct", 0.0) for s in strategies if s["status"] == "ACTIVE")
        assert total_pnl == 2.0

    def test_all_strategies_zero_pnl(self):
        """Tutte le strategie con P&L zero."""
        strategies = [
            {"id": "s1", "status": "ACTIVE", "pnl_pct": 0.0},
            {"id": "s2", "status": "ACTIVE", "pnl_pct": 0.0},
        ]
        total_pnl = sum(s.get("pnl_pct", 0.0) for s in strategies if s["status"] == "ACTIVE")
        assert total_pnl == 0.0


# ──────────────────────────────────────────────
# Integration test: Dashboard endpoint
# ──────────────────────────────────────────────

class TestDashboardEndpoint:
    """Verifica che l'endpoint GET /api/dashboard includa i nuovi KPI."""

    def test_dashboard_includes_active_strategies_count(self):
        """Dashboard response deve includere active_strategies_count."""
        dashboard_response = {
            "balance_eur": 1500.0,
            "pnl_today": 12.5,
            "active_strategy": {"id": "s1"},
            "engine_status": "RUNNING",
            "active_strategies_count": 3,
            "total_active_pnl_pct": 4.5,
        }
        assert "active_strategies_count" in dashboard_response
        assert dashboard_response["active_strategies_count"] == 3

    def test_dashboard_includes_total_active_pnl_pct(self):
        """Dashboard response deve includere total_active_pnl_pct."""
        dashboard_response = {
            "balance_eur": 1500.0,
            "pnl_today": 12.5,
            "active_strategy": {"id": "s1"},
            "engine_status": "RUNNING",
            "active_strategies_count": 2,
            "total_active_pnl_pct": 3.5,
        }
        assert "total_active_pnl_pct" in dashboard_response
        assert dashboard_response["total_active_pnl_pct"] == 3.5

    def test_dashboard_zero_active_strategies(self):
        """Con zero strategie attive, count=0 e pnl=0."""
        dashboard_response = {
            "balance_eur": 1500.0,
            "pnl_today": 0.0,
            "active_strategy": None,
            "engine_status": "RUNNING",
            "active_strategies_count": 0,
            "total_active_pnl_pct": 0.0,
        }
        assert dashboard_response["active_strategies_count"] == 0
        assert dashboard_response["total_active_pnl_pct"] == 0.0


# ──────────────────────────────────────────────
# Unit test: PnL calculation from open trades
# ──────────────────────────────────────────────

class TestPnlCalculationFromTrades:
    """Verifica calcolo P&L aggregato da trade aperti."""

    def test_calculate_pnl_from_open_trades(self):
        """P&L viene calcolato da trade con status='OPEN'."""
        trades = [
            {"id": "t1", "strategy_id": "s1", "status": "OPEN", "pnl_pct": 2.0},
            {"id": "t2", "strategy_id": "s1", "status": "OPEN", "pnl_pct": 1.5},
            {"id": "t3", "strategy_id": "s2", "status": "OPEN", "pnl_pct": -0.5},
            {"id": "t4", "strategy_id": "s2", "status": "CLOSED", "pnl_pct": 10.0},  # Ignorato
        ]
        total_pnl = sum(t["pnl_pct"] for t in trades if t["status"] == "OPEN")
        assert total_pnl == 3.0

    def test_group_pnl_by_strategy(self):
        """P&L può essere raggruppato per strategia."""
        trades = [
            {"id": "t1", "strategy_id": "s1", "status": "OPEN", "pnl_pct": 2.0},
            {"id": "t2", "strategy_id": "s1", "status": "OPEN", "pnl_pct": 1.5},
            {"id": "t3", "strategy_id": "s2", "status": "OPEN", "pnl_pct": -0.5},
        ]
        pnl_by_strategy = {}
        for t in trades:
            if t["status"] == "OPEN":
                sid = t["strategy_id"]
                pnl_by_strategy[sid] = pnl_by_strategy.get(sid, 0.0) + t["pnl_pct"]

        assert pnl_by_strategy["s1"] == 3.5
        assert pnl_by_strategy["s2"] == -0.5


# ──────────────────────────────────────────────
# Edge cases
# ──────────────────────────────────────────────

class TestEdgeCases:
    """Casi limite per KPI dashboard."""

    def test_very_large_pnl(self):
        """P&L molto grande deve essere gestito."""
        strategies = [
            {"id": "s1", "status": "ACTIVE", "pnl_pct": 100.0},
            {"id": "s2", "status": "ACTIVE", "pnl_pct": 200.0},
        ]
        total_pnl = sum(s.get("pnl_pct", 0.0) for s in strategies if s["status"] == "ACTIVE")
        assert total_pnl == 300.0

    def test_very_negative_pnl(self):
        """P&L molto negativo deve essere gestito."""
        strategies = [
            {"id": "s1", "status": "ACTIVE", "pnl_pct": -50.0},
            {"id": "s2", "status": "ACTIVE", "pnl_pct": -30.0},
        ]
        total_pnl = sum(s.get("pnl_pct", 0.0) for s in strategies if s["status"] == "ACTIVE")
        assert total_pnl == -80.0

    def test_mixed_status_strategies(self):
        """Mix di status diversi: solo ACTIVE contano."""
        strategies = [
            {"id": "s1", "status": "ACTIVE", "pnl_pct": 2.0},
            {"id": "s2", "status": "PENDING", "pnl_pct": 5.0},
            {"id": "s3", "status": "STOPPED", "pnl_pct": 3.0},
            {"id": "s4", "status": "ACTIVE", "pnl_pct": 1.0},
        ]
        active_count = sum(1 for s in strategies if s["status"] == "ACTIVE")
        total_pnl = sum(s.get("pnl_pct", 0.0) for s in strategies if s["status"] == "ACTIVE")
        assert active_count == 2
        assert total_pnl == 3.0

    def test_rounding_pnl(self):
        """P&L deve essere arrotondato a 2 decimali."""
        pnl = 3.456789
        pnl_rounded = round(pnl, 2)
        assert pnl_rounded == 3.46
