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