"""Tests for TASK-1249: update_params usabile + parametri strategia nel contesto AI.

Verifica che:
1. update_params() faccia merge sui DEFAULT_PARAMS (non sostituzione distruttiva).
2. get_params() esponga i parametri correnti.
3. Le 3 strategie concrete leggano effettivamente self._params in evaluate()
   (modifica del comportamento a runtime — prima i parametri erano hardcoded).
"""

from datetime import datetime, timezone
from decimal import Decimal

from app.scalping.models.market import Candle
from app.scalping.strategies.base import AbstractScalpingStrategy
from app.scalping.strategies.ema_cross import EMACrossStrategy
from app.scalping.strategies.rsi_bollinger import RSIBollingerStrategy
from app.scalping.strategies.vwap_reversion import VWAPReversionStrategy


def _make_candles(
    closes: list[float],
    spread: float = 10.0,
    volume: float = 100.0,
) -> list[Candle]:
    """Crea candele 1m con spread controllato."""
    now = datetime.now(timezone.utc)
    return [
        Candle(
            symbol="BTC-EUR",
            open=Decimal(str(c)),
            high=Decimal(str(c + spread)),
            low=Decimal(str(c - spread)),
            close=Decimal(str(c)),
            volume=Decimal(str(volume)),
            timestamp=now,
        )
        for c in closes
    ]


def _trending_up_candles(n: int = 30, start: float = 50000.0) -> list[Candle]:
    """Candele in uptrend con pendenza marcata (~0.1%/candela → >0.2% slope)."""
    step = start * 0.001  # 0.1% per candela → slope regressione ~0.25%
    return _make_candles([start + i * step for i in range(n)], spread=5.0)


def _vwap_dip_candles(base: float = 50000.0) -> list[Candle]:
    """15 candele flat + 10 in calo del 0.8% → ultimo close sotto VWAP di ~0.6%."""
    closes = [base] * 15
    dip = base * 0.008  # 0.8% di dip
    for i in range(10):
        closes.append(base - dip * (i + 1) / 10)
    return _make_candles(closes, spread=20.0)


class TestBaseStrategyParams:
    """TASK-1249: DEFAULT_PARAMS / get_params / update_params merge."""

    def test_default_params_exposed(self):
        """get_params() restituisce i DEFAULT_PARAMS a istanza fresca."""
        s = VWAPReversionStrategy()
        assert s.get_params() == s.DEFAULT_PARAMS

    def test_update_params_merge_partial(self):
        """update_params merge parziale: parametri non specificati mantengono default."""
        s = VWAPReversionStrategy()
        s.update_params({"vwap_distance_buy": 0.001})
        params = s.get_params()
        assert params["vwap_distance_buy"] == 0.001
        assert params["vwap_lookback"] == 20  # non toccato

    def test_update_params_not_destructive(self):
        """update_params non deve perdere i parametri non specificati (regressione)."""
        s = EMACrossStrategy()
        s.update_params({"min_slope": 0.0005})
        params = s.get_params()
        assert params["min_slope"] == 0.0005
        assert params["fast_period"] == 9  # non andato perso
        assert params["slow_period"] == 21  # non andato perso

    def test_update_params_empty_noop(self):
        """update_params({}) non altera i parametri."""
        s = RSIBollingerStrategy()
        before = s.get_params()
        s.update_params({})
        assert s.get_params() == before

    def test_get_params_returns_copy(self):
        """get_params() restituisce una copia — mutare il risultato non tocca lo stato."""
        s = VWAPReversionStrategy()
        p = s.get_params()
        p["vwap_distance_buy"] = 0.999
        assert s.get_params()["vwap_distance_buy"] == 0.002


class TestStrategiesFollowParams:
    """TASK-1249: le strategie devono leggere self._params in evaluate()."""

    def test_ema_cross_min_slope_blocks_buy(self):
        """min_slope alto → nessun BUY su un trend che con default lo produceva."""
        candles = _trending_up_candles()
        ind = AbstractScalpingStrategy.calculate_indicators(candles)

        # Con default min_slope=0.0003 il BUY scatta (slope del trend > soglia)
        s_default = EMACrossStrategy()
        sig_default = s_default.evaluate(candles, ind)
        assert sig_default.type == "BUY"

        # Con min_slope molto alto (5%) il BUY non scatta più
        s_strict = EMACrossStrategy()
        s_strict.update_params({"min_slope": 0.05})
        sig_strict = s_strict.evaluate(candles, ind)
        assert sig_strict.type == "NONE"

    def test_vwap_distance_buy_controls_signal(self):
        """vwap_distance_buy alto → BUY non scatta su dip moderato."""
        candles = _vwap_dip_candles()

        # Default vwap_distance_buy=0.002 (0.2%) → dip ~0.6% supera la soglia → BUY
        s_default = VWAPReversionStrategy()
        sig_default = s_default.evaluate(candles)
        assert sig_default.type == "BUY"

        # vwap_distance_buy=0.01 (1%) → dip ~0.6% NON supera la soglia → NONE
        s_strict = VWAPReversionStrategy()
        s_strict.update_params({"vwap_distance_buy": 0.01})
        sig_strict = s_strict.evaluate(candles)
        assert sig_strict.type == "NONE"

    def test_rsi_bollinger_oversold_threshold(self):
        """rsi_oversold più severo → BUY non scatta con RSI moderatamente basso."""
        # 15 candele flat + 10 in calo marcato (0.6%/candela) → RSI basso ma legato
        # alle BB (ultima close vicina a bb_lower)
        base = 50000.0
        closes = [base] * 15
        step = base * 0.006  # 0.6% per candela
        for i in range(10):
            closes.append(base - step * (i + 1))
        candles = _make_candles(closes, spread=15.0)
        ind = AbstractScalpingStrategy.calculate_indicators(candles)

        # Con soglie default (oversold 33-48 per fascia ATR%) il BUY scatta
        s_default = RSIBollingerStrategy()
        sig_default = s_default.evaluate(candles, ind)
        assert sig_default.type == "BUY"

        # Con oversold=0 (minimo assoluto, RSI non può essere < 0) il BUY non scatta più.
        # Questo prova che evaluate() legge self._params e non i default hardcoded.
        s_strict = RSIBollingerStrategy()
        s_strict.update_params({"rsi_oversold": [0, 0, 0, 0]})
        sig_strict = s_strict.evaluate(candles, ind)
        assert sig_strict.type == "NONE"
