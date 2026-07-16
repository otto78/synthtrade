"""Tests for TASK-904: StrategySelector + RegimeAllowed DB-driven."""

from unittest.mock import patch, MagicMock

import pytest

from app.scalping.config_loader import (
    ScalpingConfigLoader,
    _DEFAULT_REGIME_STRATEGY_MAP,
    _DEFAULT_REGIME_ALLOWED_STRATEGIES,
)
from app.scalping.engine.strategy_selector import StrategySelector
from app.scalping.models.market import MarketRegime


class TestConfigLoaderRegimeDefaults:
    """Verifica che i default siano corretti e accessibili."""

    def test_default_regime_strategy_map_has_all_regimes(self):
        expected = {"trending_up", "trending_down", "ranging", "volatile", "unknown"}
        assert set(_DEFAULT_REGIME_STRATEGY_MAP.keys()) == expected

    def test_default_regime_allowed_has_all_regimes(self):
        expected = {"ranging", "volatile", "trending_up", "trending_down", "unknown"}
        assert set(_DEFAULT_REGIME_ALLOWED_STRATEGIES.keys()) == expected

    def test_defaults_are_consistent(self):
        """Ogni strategia in _DEFAULT è anche in _ALLOWED per lo stesso regime."""
        for regime, strategy in _DEFAULT_REGIME_STRATEGY_MAP.items():
            allowed = _DEFAULT_REGIME_ALLOWED_STRATEGIES.get(regime, [])
            assert strategy in allowed, f"{regime}: default '{strategy}' not in allowed {allowed}"


class TestConfigLoaderRegimeProperties:
    """Verifica le proprietà DB-driven del config loader."""

    def _make_loader(self, db_rows=None):
        """Crea un loader mockato con righe DB opzionali."""
        mock_settings = MagicMock()
        mock_settings.scalping.SCALPING_TRADE_VALUE = 20.0
        mock_settings.scalping.SCALPING_MAX_DAILY_LOSS = 0.03
        mock_settings.scalping.SCALPING_MAX_DRAWDOWN_PCT = 0.05
        mock_settings.scalping.SCALPING_STOP_LOSS_PCT = 0.005
        mock_settings.scalping.SCALPING_TAKE_PROFIT_PCT = 0.008
        mock_settings.scalping.SCALPING_SIGNAL_STRENGTH_THRESHOLD = 15.0
        mock_settings.scalping.SCALPING_MIN_CONFIDENCE = 0.6
        mock_settings.scalping.SCALPING_MIN_COLLECTORS = 3
        mock_settings.scalping.SCALPING_SUPERVISOR_INTERVAL_SEC = 600
        mock_settings.scalping.SCALPING_STRATEGY_COOLDOWN_SEC = 1200
        mock_settings.scalping.SCALPING_PARAM_UPDATE_COOLDOWN_SEC = 600
        mock_settings.scalping.SCALPING_SUPERVISOR_MIN_TRADES_BEFORE_CHANGE = 5
        mock_settings.scalping.SCALPING_SUPERVISOR_MAX_REPEAT_DECISIONS = 3
        mock_settings.scalping.SCALPING_REGIME_TREND_THRESHOLD_PCT = 0.3
        mock_settings.scalping.SCALPING_REGIME_VOLATILE_THRESHOLD = 0.01
        mock_settings.scalping.SCALPING_TA_VOLUME_ANOMALY_MULTIPLIER = 2.0

        mock_supabase = MagicMock()
        if db_rows is not None:
            mock_supabase.table.return_value.select.return_value.execute.return_value.data = db_rows
        else:
            mock_supabase.table.return_value.select.return_value.execute.return_value.data = []

        with patch("app.scalping.config_loader.settings", mock_settings), \
             patch("app.scalping.config_loader.get_supabase", return_value=mock_supabase):
            return ScalpingConfigLoader()

    def test_regime_strategy_map_returns_defaults(self):
        loader = self._make_loader()
        result = loader.regime_strategy_map
        assert result == dict(_DEFAULT_REGIME_STRATEGY_MAP)

    def test_regime_allowed_strategies_returns_defaults(self):
        loader = self._make_loader()
        result = loader.regime_allowed_strategies
        assert result == {k: list(v) for k, v in _DEFAULT_REGIME_ALLOWED_STRATEGIES.items()}

    def test_db_override_regime_strategy(self):
        """Override singola chiave da DB."""
        db_rows = [
            {"key": "REGIME_STRATEGY_ranging", "value": "ema_cross", "value_type": "str"},
        ]
        loader = self._make_loader(db_rows)
        result = loader.regime_strategy_map
        assert result["ranging"] == "ema_cross"
        assert result["trending_up"] == "ema_cross"  # non sovrascritto

    def test_db_override_regime_allowed(self):
        """Override lista consentite da DB (comma-separated)."""
        db_rows = [
            {"key": "REGIME_ALLOWED_ranging", "value": "ema_cross,rsi_bollinger", "value_type": "str"},
        ]
        loader = self._make_loader(db_rows)
        result = loader.regime_allowed_strategies
        assert result["ranging"] == ["ema_cross", "rsi_bollinger"]

    def test_db_empty_value_keeps_default(self):
        """Valore vuoto in DB → usa default."""
        db_rows = [
            {"key": "REGIME_STRATEGY_ranging", "value": "", "value_type": "str"},
        ]
        loader = self._make_loader(db_rows)
        result = loader.regime_strategy_map
        assert result["ranging"] == _DEFAULT_REGIME_STRATEGY_MAP["ranging"]

    def test_db_none_rows_keeps_defaults(self):
        """DB restituisce None → usa default."""
        loader = self._make_loader(db_rows=None)
        result = loader.regime_strategy_map
        assert result == dict(_DEFAULT_REGIME_STRATEGY_MAP)


class TestStrategySelectorDBDriven:
    """Verifica che StrategySelector legge da config_loader."""

    def test_select_uses_config_loader(self):
        """StrategySelector senza argomenti usa config_loader."""
        selector = StrategySelector()
        regime = MarketRegime(regime="trending_up", confidence=0.8)
        strategy = selector.select(regime)
        assert strategy.name == "ema_cross"

    def test_select_custom_map_overrides(self):
        """Map iniettata sovrascrive config_loader."""
        custom = {"trending_up": "momentum_base"}
        selector = StrategySelector(regime_strategy_map=custom)
        regime = MarketRegime(regime="trending_up", confidence=0.8)
        strategy = selector.select(regime)
        assert strategy.name == "momentum_base"

    def test_get_name_for_regime_from_config(self):
        selector = StrategySelector()
        regime = MarketRegime(regime="volatile", confidence=0.7)
        assert selector.get_name_for_regime(regime) == "stoch_rsi_bb_squeeze"

    def test_unknown_regime_defaults_to_ema_cross(self):
        """Regime non mappato → fallback ema_cross."""
        selector = StrategySelector()
        regime = MarketRegime(regime="nonexistent_regime", confidence=0.5)
        strategy = selector.select(regime)
        assert strategy.name == "ema_cross"


class TestSupervisorSchedulerRegimeAllowed:
    """Verifica che il supervisor usi config_loader per regime allowed."""

    def test_fallback_dict_matches_defaults(self):
        """Il fallback hardcoded nel scheduler corrisponde ai default."""
        from app.scalping.supervisor.supervisor_scheduler import _FALLBACK_REGIME_ALLOWED_STRATEGIES
        assert _FALLBACK_REGIME_ALLOWED_STRATEGIES == {
            "ranging":        ["rsi_bollinger", "momentum_base", "stoch_rsi_bb_squeeze"],
            "volatile":       ["stoch_rsi_bb_squeeze", "momentum_base"],
            "trending_up":    ["ema_cross"],
            "trending_down":  ["ema_cross"],
            "unknown":        ["momentum_base"],
        }
