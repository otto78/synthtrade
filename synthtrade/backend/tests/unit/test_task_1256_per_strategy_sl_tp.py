"""TASK-1256: SL/TP e trailing cap per-strategia con fallback al globale.

Copre i criteri di accettazione:
- fallback: nessuna chiave STRATEGY_<NAME>_*_PCT → usa il valore globale
- override: chiave presente → usa il valore della strategia
- _effective_tp_net_pct (break_even): il cap del trailing segue il TP per-strategia
"""

import pytest

from app.scalping.config_loader import ScalpingConfigLoader


class _FakeLoader:
    """Loader minimale: ritorna override predefiniti a tabella."""

    def __init__(self, sl_map=None, tp_map=None):
        self._sl = sl_map or {}
        self._tp = tp_map or {}

    def strategy_sl_pct_override(self, name):
        return self._sl.get(name)

    def strategy_tp_pct_override(self, name):
        return self._tp.get(name)


def _bare_loader(config: dict) -> ScalpingConfigLoader:
    """ScalpingConfigLoader senza __init__ (niente DB/.env), con _config iniettato."""
    loader = ScalpingConfigLoader.__new__(ScalpingConfigLoader)
    loader._config = config
    return loader


class TestConfigLoaderStrategyOverrides:
    def test_fallback_none_when_key_absent(self):
        loader = _bare_loader({})
        assert loader.strategy_sl_pct_override("ema_cross") is None
        assert loader.strategy_tp_pct_override("ema_cross") is None

    def test_none_when_strategy_name_missing(self):
        loader = _bare_loader({"STRATEGY_EMA_CROSS_SL_PCT": 0.6})
        assert loader.strategy_sl_pct_override(None) is None
        assert loader.strategy_sl_pct_override("") is None

    def test_override_returned_when_key_present(self):
        loader = _bare_loader({
            "STRATEGY_EMA_CROSS_SL_PCT": 0.6,
            "STRATEGY_EMA_CROSS_TP_PCT": "1.2",  # dal DB puo' arrivare stringa
        })
        assert loader.strategy_sl_pct_override("ema_cross") == 0.6
        assert loader.strategy_tp_pct_override("ema_cross") == 1.2

    def test_built_in_default_rsi_bollinger_present(self):
        """I default di fabbrica STRATEGY_RSI_BOLLINGER_SL/TP_PCT sono nel loader base."""
        loader = _bare_loader({
            "STRATEGY_RSI_BOLLINGER_SL_PCT": 0.30,
            "STRATEGY_RSI_BOLLINGER_TP_PCT": 0.55,
        })
        assert loader.strategy_sl_pct_override("rsi_bollinger") == 0.30
        assert loader.strategy_tp_pct_override("rsi_bollinger") == 0.55


class TestPerStrategySlTpPct:
    def _state_with_strategy(self, name):
        class _S:
            pass
        strategy = _S()
        strategy.name = name
        loop = _S()
        loop._strategy = strategy
        return {"loop": loop}

    def test_fallback_to_global_without_loop(self, monkeypatch):
        from app.scalping.candle_processor import _per_strategy_sl_tp_pct
        monkeypatch.setattr(
            "app.scalping.candle_processor.get_scalping_config",
            lambda: _FakeLoader({"rsi_bollinger": 0.35}, {"rsi_bollinger": 0.55}),
        )
        risk_cfg = {"stop_loss_pct": 0.5, "take_profit_pct": 0.8}
        sl, tp = _per_strategy_sl_tp_pct({}, risk_cfg)
        assert (sl, tp) == (0.5, 0.8)

    def test_fallback_when_strategy_has_no_override(self, monkeypatch):
        from app.scalping.candle_processor import _per_strategy_sl_tp_pct
        monkeypatch.setattr(
            "app.scalping.candle_processor.get_scalping_config",
            lambda: _FakeLoader(),
        )
        risk_cfg = {"stop_loss_pct": 0.5, "take_profit_pct": 0.8}
        sl, tp = _per_strategy_sl_tp_pct(self._state_with_strategy("ema_cross"), risk_cfg)
        assert (sl, tp) == (0.5, 0.8)

    def test_override_wins_for_both_sl_and_tp(self, monkeypatch):
        from app.scalping.candle_processor import _per_strategy_sl_tp_pct
        monkeypatch.setattr(
            "app.scalping.candle_processor.get_scalping_config",
            lambda: _FakeLoader({"rsi_bollinger": 0.35}, {"rsi_bollinger": 0.55}),
        )
        risk_cfg = {"stop_loss_pct": 0.5, "take_profit_pct": 0.8}
        sl, tp = _per_strategy_sl_tp_pct(self._state_with_strategy("rsi_bollinger"), risk_cfg)
        assert (sl, tp) == (0.35, 0.55)

    def test_partial_override_falls_back_per_field(self, monkeypatch):
        from app.scalping.candle_processor import _per_strategy_sl_tp_pct
        monkeypatch.setattr(
            "app.scalping.candle_processor.get_scalping_config",
            lambda: _FakeLoader({"rsi_bollinger": 0.35}, {}),
        )
        risk_cfg = {"stop_loss_pct": 0.5, "take_profit_pct": 0.8}
        sl, tp = _per_strategy_sl_tp_pct(self._state_with_strategy("rsi_bollinger"), risk_cfg)
        assert (sl, tp) == (0.35, 0.8)

    def test_degrades_to_global_when_config_raises(self, monkeypatch):
        from app.scalping.candle_processor import _per_strategy_sl_tp_pct

        def boom():
            raise RuntimeError("DB non raggiungibile")

        monkeypatch.setattr("app.scalping.candle_processor.get_scalping_config", boom)
        risk_cfg = {"stop_loss_pct": 0.5, "take_profit_pct": 0.8}
        sl, tp = _per_strategy_sl_tp_pct(self._state_with_strategy("rsi_bollinger"), risk_cfg)
        assert (sl, tp) == (0.5, 0.8)


class TestEffectiveTpNetPctForTrailingCap:
    def _state_with_strategy(self, name):
        class _S:
            pass
        strategy = _S()
        strategy.name = name
        loop = _S()
        loop._strategy = strategy
        return {"loop": loop}

    def test_fallback_to_global_without_loop(self, monkeypatch):
        from app.scalping.break_even import _effective_tp_net_pct
        monkeypatch.setattr(
            "app.scalping.break_even.get_scalping_config",
            lambda: _FakeLoader(tp_map={"rsi_bollinger": 0.55}),
        )
        assert _effective_tp_net_pct({"take_profit_pct": 0.80}) == 0.80

    def test_trailing_cap_follows_strategy_tp(self, monkeypatch):
        import app.scalping.break_even as be
        monkeypatch.setattr(
            "app.scalping.break_even.get_scalping_config",
            lambda: _FakeLoader(tp_map={"rsi_bollinger": 0.55}),
        )
        old_loop = be._execution_state.get("loop")
        be._execution_state["loop"] = self._state_with_strategy("rsi_bollinger")["loop"]
        try:
            assert be._effective_tp_net_pct({"take_profit_pct": 0.80}) == 0.55
        finally:
            if old_loop is None:
                be._execution_state.pop("loop", None)
            else:
                be._execution_state["loop"] = old_loop

    def test_degrades_to_global_on_error(self, monkeypatch):
        import app.scalping.break_even as be

        def boom():
            raise RuntimeError("config non disponibile")

        monkeypatch.setattr("app.scalping.break_even.get_scalping_config", boom)
        old_loop = be._execution_state.get("loop")
        be._execution_state["loop"] = self._state_with_strategy("ema_cross")["loop"]
        try:
            assert be._effective_tp_net_pct({"take_profit_pct": 0.80}) == 0.80
        finally:
            if old_loop is None:
                be._execution_state.pop("loop", None)
            else:
                be._execution_state["loop"] = old_loop
