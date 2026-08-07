"""RSI + Bollinger Bands Strategy - filtro timing per mean reversion.

Soglie dinamiche basate sull'ATR% (volatilità) del mercato.
In range stretti (ATR% < 0.5%), le soglie statiche 38/62 non vengono mai
raggiunte — RSI oscilla 40-60. Le soglie si allargano automaticamente.

Dinamica soglie RSI:
- ATR% < 0.4% (range stretto): oversold 48, overbought 52
- ATR% 0.4-0.6%: oversold 43, overbought 57  
- ATR% 0.6-1.0%: oversold 38, overbought 62 (comportamento attuale)
- ATR% > 1.0%: oversold 33, overbought 67
"""

from typing import List, Optional

from app.scalping.models.market import Candle
from app.scalping.strategies.base import AbstractScalpingStrategy
from app.scalping.engine.signal_aggregator import TechnicalSignal


def _calculate_atr_percent(candles: List[Candle], period: int = 14) -> float:
    """Calcola ATR% (Average True Range percentuale) su N candele.
    
    ATR% = media dei True Range / prezzo close * 100
    True Range = max(high - low, abs(high - prev_close), abs(low - prev_close))
    
    Restituisce la volatilità in percentuale (es. 0.5 = 0.5%).
    Se ci sono meno di 2 candele, restituisce 0.5 (default medio).
    """
    if len(candles) < period + 1:
        return 0.5
    
    tr_sum = 0.0
    count = 0
    for i in range(-period, 0):
        prev_close = float(candles[i - 1].close)
        h = float(candles[i].high)
        l = float(candles[i].low)
        c = float(candles[i].close)
        tr = max(h - l, abs(h - prev_close), abs(l - prev_close))
        tr_sum += tr
        count += 1
    
    if count == 0:
        return 0.5
    avg_tr = tr_sum / count
    last_close = float(candles[-1].close)
    if last_close == 0:
        return 0.5
    return (avg_tr / last_close) * 100


class RSIBollingerStrategy(AbstractScalpingStrategy):
    """Strategia RSI + Bollinger Bands per mean reversion in ranging.

    Usa soglie RSI dinamiche basate sull'ATR% per adattarsi a qualsiasi
    volatilità di mercato, dai range stretti (0.3%) a quelli ampi (>1%).
    """

    # TASK-1249: parametri modificabili dal supervisor via update_params.
    # I default coincidono con i valori hardcoded storici → nessun cambio
    # di comportamento a parità di config.
    DEFAULT_PARAMS: dict = {
        "atr_thresholds": [0.4, 0.6, 1.0],      # soglie ATR% per fascia
        "rsi_oversold": [48, 43, 38, 33],       # soglia oversold per fascia
        "rsi_overbought": [52, 57, 62, 67],     # soglia overbought per fascia
        "bb_tolerance": [1.008, 1.012, 1.015, 1.020],  # tolleranza BB per fascia
        "confidence": [0.35, 0.5, 0.6, 0.7],    # confidence per fascia
    }

    @property
    def name(self) -> str:
        return "rsi_bollinger"

    def evaluate(
        self,
        candles: List[Candle],
        indicators: Optional[dict] = None,
    ) -> TechnicalSignal:
        """Valuta RSI e BB per segnale di timing con soglie dinamiche."""
        if len(candles) < 20:
            return TechnicalSignal(type="NONE", confidence=0.0)

        ind = indicators or self.calculate_indicators(candles)

        rsi = ind.get("rsi", 50)
        close = ind.get("close", 0)
        bb_lower = ind.get("bb_lower", 0)
        bb_upper = ind.get("bb_upper", 0)

        # Calcola soglie dinamiche basate su ATR%
        atr_pct = _calculate_atr_percent(candles)

        # TASK-1249: parametri letti da self._params (modificabili dal supervisor).
        # Fallback ai default hardcoded se il dict è incompleto (retrocompatibilità).
        p = self._params
        atr_thresholds = p.get("atr_thresholds", [0.4, 0.6, 1.0])
        rsi_oversold_list = p.get("rsi_oversold", [48, 43, 38, 33])
        rsi_overbought_list = p.get("rsi_overbought", [52, 57, 62, 67])
        bb_tolerance_list = p.get("bb_tolerance", [1.008, 1.012, 1.015, 1.020])
        confidence_list = p.get("confidence", [0.35, 0.5, 0.6, 0.7])

        # Mappa ATR% → soglie RSI (indice fascia = numero di soglie superate)
        idx = 0
        for i, thr in enumerate(atr_thresholds):
            if atr_pct >= thr:
                idx = i + 1
        idx = min(idx, len(rsi_oversold_list) - 1)

        rsi_oversold = rsi_oversold_list[idx]
        rsi_overbought = rsi_overbought_list[idx]
        bb_tolerance = bb_tolerance_list[idx]
        confidence = confidence_list[idx]

        # Segnale BUY: RSI oversold + prezzo vicino BB inferiore
        if rsi < rsi_oversold and close <= bb_lower * bb_tolerance:
            return TechnicalSignal(
                type="BUY",
                confidence=confidence,
                source=f"{self.name}(atr={atr_pct:.2f}%)",
            )

        # Segnale SELL: RSI overbought + prezzo vicino BB superiore
        # bb_upper / bb_tolerance = bb_upper * (1/bb_tolerance) ≈ bb_upper * 0.985
        if rsi > rsi_overbought and close >= bb_upper / bb_tolerance:
            return TechnicalSignal(
                type="SELL",
                confidence=confidence,
                source=f"{self.name}(atr={atr_pct:.2f}%)",
            )

        return TechnicalSignal(type="NONE", confidence=0.0)
