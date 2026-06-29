"""Signal Log Writer — scrittura decisioni su session_signal_log.

Questo modulo fornisce funzioni per loggare decisioni del sistema
su session_signal_log usando DecisionContextExtractor per normalizzazione.
"""

import logging
from typing import Optional
from app.core.decision_context import extract_decision_context, DecisionContext
from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)


def log_signal_decision(
    session_id: str,
    symbol: str,
    decision_type: str,
    decision_reason: Optional[str] = None,
    **context_kwargs
) -> bool:
    """Logga una decisione su session_signal_log usando DecisionContextExtractor.
    
    Args:
        session_id: ID della sessione
        symbol: Simbolo trading
        decision_type: Tipo di decisione (execute, block_conflict, mean_reversion_override, etc.)
        decision_reason: Motivo della decisione (opzionale)
        **context_kwargs: Campi contesto (regime, strategy, tech_signal, intel_score, etc.)
    
    Returns:
        True se loggato con successo, False altrimenti (non-blocking)
    
    Example:
        log_signal_decision(
            session_id="123",
            symbol="BTCUSDT",
            decision_type="execute",
            regime="ranging",
            strategy_type="rsi_bollinger",
            tech_signal="BUY",
            intel_score=0.75,
            intel_bias="bullish"
        )
    """
    try:
        # Normalizza contesto usando DecisionContextExtractor
        ctx = extract_decision_context(
            session_id=session_id,
            symbol=symbol,
            decision_type=decision_type,
            decision_reason=decision_reason,
            **context_kwargs
        )
        
        # Converti in dict per DB
        db_data = ctx.to_db_dict()
        
        # Esegui INSERT su session_signal_log
        supabase = get_supabase()
        supabase.table("session_signal_log").insert(db_data).execute()
        
        logger.debug(f"Decisione loggata su session_signal_log: {decision_type} per sessione {session_id}")
        return True
        
    except ValueError as e:
        # Errori di validazione (campi obbligatori mancanti)
        logger.error(f"Errore validazione contesto decisionale (non-blocking): {e}")
        return False
    except Exception as e:
        # Altri errori (DB, network, etc.)
        logger.error(f"Errore logging decisione su session_signal_log (non-blocking): {e}")
        return False


def log_pipeline_decision(
    session_id: str,
    symbol: str,
    regime: str,
    strategy_type: str,
    tradeable: bool,
    vol_anomaly: bool = False,
    **context_kwargs
) -> bool:
    """Logga decisione PIPELINE (esecuzione trade).
    
    Args:
        session_id: ID della sessione
        symbol: Simbolo trading
        regime: Regime del mercato
        strategy_type: Tipo di strategia
        tradeable: Se il trade è eseguibile
        vol_anomaly: Se c'è anomalia volatilità
        **context_kwargs: Altri campi contesto (tech_signal, intel_score, etc.)
    
    Returns:
        True se loggato con successo, False altrimenti
    """
    decision_type = "execute" if tradeable else "rejected_other"
    decision_reason = f"PIPELINE: regime={regime} strategy={strategy_type} vol_anomaly={vol_anomaly} tradeable={tradeable}"
    
    return log_signal_decision(
        session_id=session_id,
        symbol=symbol,
        decision_type=decision_type,
        decision_reason=decision_reason,
        regime=regime,
        strategy_type=strategy_type,
        **context_kwargs
    )


def log_block_decision(
    session_id: str,
    symbol: str,
    block_reason: str,
    **context_kwargs
) -> bool:
    """Logga decisione BLOCK (blocco conflitto).
    
    Args:
        session_id: ID della sessione
        symbol: Simbolo trading
        block_reason: Motivo del blocco
        **context_kwargs: Altri campi contesto
    
    Returns:
        True se loggato con successo, False altrimenti
    """
    return log_signal_decision(
        session_id=session_id,
        symbol=symbol,
        decision_type="block_conflict",
        decision_reason=f"BLOCK: {block_reason}",
        **context_kwargs
    )


def log_mean_reversion_decision(
    session_id: str,
    symbol: str,
    override_reason: str,
    **context_kwargs
) -> bool:
    """Logga decisione MEAN-REVERSION (override mean-reversion).
    
    Args:
        session_id: ID della sessione
        symbol: Simbolo trading
        override_reason: Motivo dell'override
        **context_kwargs: Altri campi contesto
    
    Returns:
        True se loggato con successo, False altrimenti
    """
    return log_signal_decision(
        session_id=session_id,
        symbol=symbol,
        decision_type="mean_reversion_override",
        decision_reason=f"MEAN-REVERSION override: {override_reason}",
        **context_kwargs
    )


def log_hold_decision(
    session_id: str,
    symbol: str,
    hold_reason: str,
    **context_kwargs
) -> bool:
    """Logga decisione HOLD (mantenere posizione esistente).
    
    Args:
        session_id: ID della sessione
        symbol: Simbolo trading
        hold_reason: Motivo del hold
        **context_kwargs: Altri campi contesto
    
    Returns:
        True se loggato con successo, False altrimenti
    """
    return log_signal_decision(
        session_id=session_id,
        symbol=symbol,
        decision_type="hold_existing_position",
        decision_reason=f"HOLD: {hold_reason}",
        **context_kwargs
    )


def log_execution_error(
    session_id: str,
    symbol: str,
    error_message: str,
    **context_kwargs
) -> bool:
    """Logga errore di esecuzione.
    
    Args:
        session_id: ID della sessione
        symbol: Simbolo trading
        error_message: Messaggio di errore
        **context_kwargs: Altri campi contesto
    
    Returns:
        True se loggato con successo, False altrimenti
    """
    return log_signal_decision(
        session_id=session_id,
        symbol=symbol,
        decision_type="execution_error",
        decision_reason=f"EXECUTION ERROR: {error_message}",
        **context_kwargs
    )