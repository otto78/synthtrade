"""API Router per moduli Scalping (TASK-808, TASK-809).

Endpoints:
- POST /scalping/backtest/run   — avvia backtest
- GET  /scalping/backtest/{id}/result — recupera risultato backtest
"""

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException

from app.scalping.models.backtest import (
    BacktestConfig,
    BacktestResult,
)
from app.scalping.backtest.backtest_engine import BacktestEngine
from app.scalping.backtest.historical_loader import HistoricalLoader
from app.scalping.backtest.performance_calculator import PerformanceCalculator
from app.scalping.backtest.report_generator import ReportGenerator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scalping", tags=["scalping"])

# Store backtest results in memory (in production, use DB)
_backtest_results: Dict[str, BacktestResult] = {}


@router.post("/backtest/run")
async def run_backtest(config: BacktestConfig) -> Dict:
    """Esegue un backtest per la configurazione specificata.

    Carica candele storiche da Binance API, esegue il backtest
    e restituisce il risultato con metriche di performance.

    Args:
        config: Configurazione backtest (simbolo, date, capitale, etc.).

    Returns:
        Dict con risultato del backtest (metriche, trades, report).
    """
    try:
        # 1. Carica dati storici
        loader = HistoricalLoader()
        candles = await loader.load_ohlcv(
            symbol=config.symbol,
            interval=config.timeframe,
            start=config.start_date,
            end=config.end_date,
            limit=1000,
        )

        if not candles:
            raise HTTPException(
                status_code=400,
                detail=f"Nessun dato storico trovato per {config.symbol} "
                       f"da {config.start_date.date()} a {config.end_date.date()}. "
                       "Verifica il simbolo e le date.",
            )

        # 2. Esegui backtest
        engine = BacktestEngine()
        result = await engine.run(config, candles=candles)

        # 3. Calcola metriche
        calculator = PerformanceCalculator()
        calculator.calculate(result)
        calculator.calculate_correlation(result)

        # 4. Genera report
        generator = ReportGenerator(calculator=calculator)
        report = generator.generate_report(result)

        # 5. Salva risultato
        result_id = str(uuid.uuid4())[:8]
        _backtest_results[result_id] = result

        # 6. Aggiungi id al report
        report["config"]["result_id"] = result_id

        logger.info(f"Backtest {result_id} completed: {len(result.trades)} trades, "
                     f"PnL={result.metrics.get('total_pnl', 0):.2f} USDT")

        return report

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backtest error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Backtest error: {str(e)}")


@router.get("/backtest/{result_id}/result")
async def get_backtest_result(result_id: str) -> Dict:
    """Recupera il risultato di un backtest completato.

    Args:
        result_id: ID del backtest (restituito da POST /backtest/run).

    Returns:
        Dict con risultato completo del backtest.
    """
    result = _backtest_results.get(result_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Backtest {result_id} non trovato. "
                   "Potrebbe essere scaduto o l'ID e' errato.",
        )

    generator = ReportGenerator()
    report = generator.generate_report(result)

    report["config"]["result_id"] = result_id
    return report


@router.get("/backtest/list")
async def list_backtests() -> List[Dict]:
    """Lista tutti i backtest eseguiti nella sessione corrente.

    Returns:
        Lista di riepiloghi backtest (id, simbolo, date, metriche principali).
    """
    summaries = []
    for rid, result in _backtest_results.items():
        m = result.metrics
        summaries.append({
            "id": rid,
            "symbol": result.config.symbol,
            "start_date": result.config.start_date.isoformat(),
            "end_date": result.config.end_date.isoformat(),
            "total_trades": m.get("total_trades", 0),
            "total_pnl": m.get("total_pnl", 0),
            "win_rate": m.get("win_rate", 0),
            "completed_at": result.completed_at.isoformat() if result.completed_at else None,
        })
    return summaries


# Intelligence endpoints
@router.get("/intelligence/{symbol}/snapshot")
async def get_intel_snapshot(symbol: str) -> Dict:
    """Get latest market intelligence snapshot for symbol."""
    # TODO: Connect to SignalScoreEngine
    return {
        "symbol": symbol,
        "funding_rate": 0.0,
        "open_interest": 0,
        "signal_score": 50,
        "bias": "neutral",
    }


@router.get("/intelligence/{symbol}/history")
async def get_intel_history(symbol: str, limit: int = 100) -> List[Dict]:
    """Get historical intelligence snapshots."""
    return []


# Opportunity endpoints
@router.get("/opportunities")
async def get_opportunities(
    urgency: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
) -> List[Dict]:
    """Get opportunities list with filters."""
    # TODO: Connect to OpportunityRouter
    return []


# Session endpoints
_session_state: Dict = {
    "session_id": None,
    "status": "idle",
    "mode": "paper",
    "strategy": "scalping_v2",
    "symbol": "BTCUSDT",
    "paper_balance": 10000.0,
}


@router.get("/session")
async def get_session() -> Dict:
    """Get current session status."""
    return _session_state.copy()


@router.post("/session")
async def control_session(control: Dict) -> Dict:
    """Control session: start, stop, pause, resume."""
    global _session_state

    action = control.get("action")

    if action == "start":
        _session_state["status"] = "running"
        _session_state["session_id"] = f"sess_{uuid.uuid4().hex[:8]}"
        _session_state["mode"] = control.get("mode", "paper")
        _session_state["strategy"] = control.get("strategy", "scalping_v2")
        _session_state["symbol"] = control.get("symbol", "BTCUSDT")

    elif action == "stop":
        _session_state = {
            "session_id": None,
            "status": "idle",
            "mode": "paper",
            "strategy": "scalping_v2",
            "symbol": "BTCUSDT",
            "paper_balance": _session_state.get("paper_balance", 10000.0),
        }

    elif action == "pause":
        if _session_state["status"] == "running":
            _session_state["status"] = "paused"

    elif action == "resume":
        if _session_state["status"] == "paused":
            _session_state["status"] = "running"

    return _session_state.copy()
# Position endpoints
@router.get("/position")
async def get_position() -> Optional[Dict]:
    """Get current open position."""
    # TODO: Connect to PositionManager
    return None


@router.get("/position/list")
async def list_positions() -> List[Dict]:
    """List all positions."""
    return []


# Performance endpoint
@router.get("/performance")
async def get_performance() -> Dict:
    """Get performance metrics."""
    return {
        "total_pnl": 0,
        "total_pnl_pct": 0,
        "win_rate": 0,
        "total_trades": 0,
        "winning_trades": 0,
        "losing_trades": 0,
        "profit_factor": 0,
        "max_drawdown": 0,
    }
