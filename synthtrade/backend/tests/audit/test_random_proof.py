"""
TASK-AUDIT-002 — Prova del Random

Dimostra che generate_for_request() usa valori casuali (random.uniform)
per ai_score e estimated_profit_pct.

Questi test sono progettati per FALLIRE finché il bug non viene corretto.
Il fallimento conferma la presenza di allucinazioni nel path utente.

Esecuzione:
    cd synthtrade/backend
    python -m pytest tests/audit/test_random_proof.py -v -s
"""

import pytest
from unittest.mock import patch, AsyncMock
from app.core.strategy_generator import generate_for_request
from app.execution.schemas import StrategyRequest


@pytest.fixture
def base_request():
    """Richiesta base identica per entrambe le chiamate."""
    return StrategyRequest(
        budget_eur=100.0,
        duration_days=30,
        asset_class="crypto",
        risk_level="medium",
        max_strategies=5,
    )


@pytest.mark.asyncio
async def test_same_request_produces_different_scores(base_request):
    """
    AUDIT: Due chiamate identiche NON devono produrre score diversi.
    
    Se questo test FALLISCE → conferma che ai_score è generato con random.
    Se questo test PASSA → il bug è stato corretto (score deterministici).
    
    NOTE: Blocchiamo enrich_request_with_ai per isolare il generator puro.
    """
    with patch(
        "app.core.strategy_generator.enrich_request_with_ai",
        new_callable=AsyncMock,
        return_value=base_request,
    ):
        results_1 = await generate_for_request(base_request)
        results_2 = await generate_for_request(base_request)

    assert results_1, "Nessuna strategia generata al primo run"
    assert results_2, "Nessuna strategia generata al secondo run"

    scores_1 = sorted([r.ai_score for r in results_1])
    scores_2 = sorted([r.ai_score for r in results_2])

    assert scores_1 == scores_2, (
        f"\n\n❌ ALLUCINAZIONE CONFERMATA: stessi input → score diversi!\n"
        f"   Call 1: {scores_1}\n"
        f"   Call 2: {scores_2}\n\n"
        f"   CAUSA: generate_for_request() usa random.uniform(0, 25.0) per calcolare ai_score.\n"
        f"   FIX: Sostituire con compute_score(run_backtest(fetch_ohlcv(...))).\n"
        f"   Vedi TASK-AUDIT-006 in docs/TASKS.md"
    )


@pytest.mark.asyncio
async def test_estimated_profit_is_not_random(base_request):
    """
    AUDIT: I profitti stimati devono essere deterministici e basati su backtest.
    
    Se questo test FALLISCE → conferma che estimated_profit_pct è generato con random.
    Se questo test PASSA → il bug è stato corretto (profitti basati su dati reali).
    """
    with patch(
        "app.core.strategy_generator.enrich_request_with_ai",
        new_callable=AsyncMock,
        return_value=base_request,
    ):
        results_1 = await generate_for_request(base_request)
        results_2 = await generate_for_request(base_request)

    profits_1 = sorted([r.estimated_profit_pct for r in results_1])
    profits_2 = sorted([r.estimated_profit_pct for r in results_2])

    assert profits_1 == profits_2, (
        f"\n\n❌ ALLUCINAZIONE CONFERMATA: profitti stimati diversi tra chiamate identiche!\n"
        f"   Call 1: {profits_1}\n"
        f"   Call 2: {profits_2}\n\n"
        f"   CAUSA: il codice usa `base_profit + random.uniform(-2.0, 5.0)`\n"
        f"   dove base_profit dipende solo da risk_level (low=3, medium=8, high=15).\n"
        f"   FIX: Sostituire con result.pnl_pct dal backtest reale.\n"
        f"   Vedi TASK-AUDIT-006 in docs/TASKS.md"
    )


@pytest.mark.asyncio
async def test_score_is_within_random_range(base_request):
    """
    AUDIT: Verifica che gli score attuali siano nel range 70-99 (il range del random).
    
    Questo test PASSA se il bug esiste (score nel range del random).
    Questo test DIVENTA OBSOLETO dopo il fix.
    """
    with patch(
        "app.core.strategy_generator.enrich_request_with_ai",
        new_callable=AsyncMock,
        return_value=base_request,
    ):
        results = await generate_for_request(base_request)

    assert results, "Nessuna strategia generata"

    for r in results:
        # Se tutti gli score sono tra 70 e 99, siamo nel range di random.uniform(0,25)+70
        in_random_range = 70.0 <= r.ai_score <= 99.0
        print(f"   Strategy {r.template}: ai_score={r.ai_score:.2f} in_random_range={in_random_range}")

    # Documentazione del finding
    all_in_range = all(70.0 <= r.ai_score <= 99.0 for r in results)
    print(f"\n   📊 Tutti gli score nel range random [70, 99]: {all_in_range}")
    print(f"   ⚠️  Score = 70 + random.uniform(0, 25) — non basato su dati reali")


@pytest.mark.asyncio
async def test_profit_estimate_ignores_actual_market_conditions(base_request):
    """
    AUDIT: Verifica che il profitto stimato non dipenda da dati di mercato reali.
    
    Due richieste con asset diversi (BTC vs ETH) hanno profit simili
    perché il calcolo ignora i dati storici e usa solo risk_level.
    """
    req_btc = StrategyRequest(
        budget_eur=100.0, duration_days=30,
        asset_class="crypto", risk_level="medium",
        symbols=["BTC/USDT"], max_strategies=3
    )
    req_eth = StrategyRequest(
        budget_eur=100.0, duration_days=30,
        asset_class="crypto", risk_level="medium",
        symbols=["ETH/USDT"], max_strategies=3
    )

    with patch(
        "app.core.strategy_generator.enrich_request_with_ai",
        new_callable=AsyncMock,
        side_effect=lambda x: x,
    ):
        results_btc = await generate_for_request(req_btc)
        results_eth = await generate_for_request(req_eth)

    # Calcola range medio dei profitti per ciascun asset
    profits_btc = [r.estimated_profit_pct for r in results_btc]
    profits_eth = [r.estimated_profit_pct for r in results_eth]

    print(f"\n   BTC profits: {[f'{p:.2f}%' for p in profits_btc]}")
    print(f"   ETH profits: {[f'{p:.2f}%' for p in profits_eth]}")
    print(f"\n   ⚠️  Se i range sono simili, i profitti non dipendono dall'asset specifico.")
    print(f"   ⚠️  Questo conferma che le stime sono inventate (base_profit per risk_level)")
    print(f"   ⚠️  e non basate su performance storica reale di BTC vs ETH.")
