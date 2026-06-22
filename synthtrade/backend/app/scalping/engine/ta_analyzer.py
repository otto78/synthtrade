import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class TAAnalyzer:
    """
    Analizzatore per Technical Analysis (TA) e Volumi.
    Calcola pattern candlestick, anomalie volumetriche e vicinanza S/R.
    """

    @staticmethod
    def analyze_candlesticks(candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Riconosce i pattern candlestick usando pandas-ta.
        Restituisce un dizionario con i pattern bullish e bearish trovati sull'ultima candela.
        """
        if len(candles) < 10:
            return {"bullish": [], "bearish": [], "score": 0}
            
        import pandas as pd
        import pandas_ta as ta

        # Creazione DataFrame
        df = pd.DataFrame(candles)
        for col in ['open', 'high', 'low', 'close']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # Lista dei pattern di inversione più comuni/forti per non appesantire il loop
        patterns = ["hammer", "shootingstar", "morningstar", "eveningstar", "engulfing", "doji", "harami", "piercing", "darkcloudcover"]
        cdl = df.ta.cdl_pattern(name=patterns)
        
        if cdl is None or cdl.empty:
            return {"bullish": [], "bearish": [], "score": 0}
            
        # Analizziamo l'ultima candela chiusa
        last_row = cdl.iloc[-1]
        
        bullish_patterns = []
        bearish_patterns = []
        
        for col in last_row.index:
            val = last_row[col]
            if val > 0:
                bullish_patterns.append(col)
            elif val < 0:
                bearish_patterns.append(col)
                
        return {
            "bullish": bullish_patterns,
            "bearish": bearish_patterns,
            "score": len(bullish_patterns) - len(bearish_patterns)
        }

    @staticmethod
    def detect_volume_anomaly(candles: List[Dict[str, Any]], multiplier: float = 2.0) -> bool:
        """
        Rileva se l'ultima candela ha un volume >= `multiplier` rispetto alla media mobile del volume.
        """
        if len(candles) < 10:
            return False
            
        volumes = [float(c.get('volume', 0)) for c in candles[-10:-1]]
        if not volumes:
            return False
            
        avg_volume = sum(volumes) / len(volumes)
        last_volume = float(candles[-1].get('volume', 0))
        
        if avg_volume > 0 and last_volume >= avg_volume * multiplier:
            return True
            
        return False

    @staticmethod
    def get_support_resistance_data(current_price: float, levels: List[float]) -> Dict[str, Any]:
        """
        Restituisce la distanza percentuale dai livelli di supporto e resistenza più vicini.
        `levels` = lista pre-calcolata di livelli S/R.
        """
        if not levels:
            return {"nearest_support": None, "nearest_resistance": None}
            
        supports = [l for l in levels if l < current_price]
        resistances = [l for l in levels if l > current_price]
        
        closest_supp = max(supports) if supports else None
        closest_res = min(resistances) if resistances else None
        
        return {
            "nearest_support": closest_supp,
            "support_distance_pct": round((current_price - closest_supp) / closest_supp * 100, 2) if closest_supp else None,
            "nearest_resistance": closest_res,
            "resistance_distance_pct": round((closest_res - current_price) / current_price * 100, 2) if closest_res else None,
        }
