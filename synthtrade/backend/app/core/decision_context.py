"""Decision Context Extractor — normalizza l'estrazione del contesto decisionale.

Questo modulo fornisce una dataclass DecisionContext e una funzione di estrazione
per normalizzare il contesto decisionale, evitando duplicazione tra:
- TASK-894 (scrittura su session_signal_log)
- SessionLogHandler (analisi log legacy)
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from datetime import datetime, timezone


@dataclass
class DecisionContext:
    """Dataclass che rappresenta il contesto completo di una decisione.
    
    Tutti i campi sono opzionali tranne quelli richiesti dallo schema DB.
    Usare extract_decision_context() per costruire istanze validas.
    """
    session_id: str
    symbol: str
    regime: str
    strategy_type: str
    tech_signal: Optional[str] = None          # BUY/SELL/HOLD/CLOSE
    tech_confidence: Optional[float] = None
    intel_score: Optional[float] = None
    intel_bias: Optional[str] = None           # bullish/bearish/neutral
    trend_direction: Optional[str] = None      # converging/diverging/stable
    trend_value: Optional[float] = None
    decision_type: Optional[str] = None        # execute/block_conflict/...
    decision_reason: Optional[str] = None
    trade_id: Optional[str] = None
    decided_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte in dict per INSERT su DB, rimuovendo None se richiesto."""
        return asdict(self)
    
    def to_db_dict(self) -> Dict[str, Any]:
        """Converte in dict per DB, rimuovendo None e converting datetime."""
        result = {}
        for key, value in self.to_dict().items():
            if value is not None:
                if key == 'decided_at' and isinstance(value, datetime):
                    result[key] = value.isoformat()
                else:
                    result[key] = value
        return result


def extract_decision_context(**kwargs) -> DecisionContext:
    """Normalizza e valida il contesto decisionale dai parametri kwargs.
    
    Args:
        **kwargs: Contesto decisionale dal runtime (regime, strategy, intel_score, etc.)
    
    Returns:
        DecisionContext: Istanza validata con campi obbligatori verificati
    
    Raises:
        ValueError: Se campi obbligatori mancanti (session_id, symbol, regime, strategy_type)
    
    Example:
        ctx = extract_decision_context(
            session_id="123",
            symbol="BTCUSDT",
            regime="ranging",
            strategy_type="rsi_bollinger",
            tech_signal="BUY",
            intel_score=0.75,
            intel_bias="bullish",
            trend_direction="converging",
            decision_type="execute"
        )
    """
    # Campi obbligatori
    required_fields = ['session_id', 'symbol', 'regime', 'strategy_type']
    for field in required_fields:
        if field not in kwargs or kwargs[field] is None:
            raise ValueError(f"Campo obbligatorio mancante: {field}")
    
    # Creare DecisionContext con normalizzazione
    ctx = DecisionContext(
        session_id=str(kwargs['session_id']),
        symbol=str(kwargs['symbol']),
        regime=str(kwargs['regime']),
        strategy_type=str(kwargs['strategy_type']),
        tech_signal=kwargs.get('tech_signal'),
        tech_confidence=kwargs.get('tech_confidence'),
        intel_score=kwargs.get('intel_score'),
        intel_bias=kwargs.get('intel_bias'),
        trend_direction=kwargs.get('trend_direction'),
        trend_value=kwargs.get('trend_value'),
        decision_type=kwargs.get('decision_type'),
        decision_reason=kwargs.get('decision_reason'),
        trade_id=kwargs.get('trade_id'),
        decided_at=kwargs.get('decided_at') or datetime.now(timezone.utc)
    )
    
    return ctx


def extract_from_pipeline_log(log_message: str, session_id: str, symbol: str) -> Optional[DecisionContext]:
    """Estrae DecisionContext da un messaggio di log PIPELINE (compatibilità legacy).
    
    Questa funzione permette di estrarre contesto dai log testuali esistenti
    per sessioni pre-migrazione, mantenendo compatibilità con SessionLogHandler.
    
    Args:
        log_message: Messaggio di log PIPELINE esistente
        session_id: ID sessione
        symbol: Simbolo trading
    
    Returns:
        DecisionContext se parsing riuscito, None altrimenti
    """
    import re
    
    # Esempio pattern: "PIPELINE: regime=ranging strategy=rsi_bollinger vol_anomaly=True ..."
    regime_match = re.search(r'regime=(\w+)', log_message)
    strategy_match = re.search(r'strategy=(\w+)', log_message)
    
    if not regime_match or not strategy_match:
        return None
    
    return DecisionContext(
        session_id=session_id,
        symbol=symbol,
        regime=regime_match.group(1),
        strategy_type=strategy_match.group(1),
        decision_type='execute' if 'tradeable=True' in log_message else 'rejected',
        decision_reason=log_message
    )