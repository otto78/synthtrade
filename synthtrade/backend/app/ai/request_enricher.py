import json
import logging
from app.execution.schemas import StrategyRequest
from app.ai.model_client import ModelClient, AllModelsUnavailableError
from app.config import settings

logger = logging.getLogger(__name__)

def get_model_client() -> ModelClient:
    return ModelClient(
        api_key=settings.AI_API_KEY,
        api_base_url=settings.AI_API_BASE_URL,
        cascade_models=settings.ai_cascade_models_list,
        fallback_model=settings.AI_FALLBACK_MODEL,
        timeout=settings.AI_TIMEOUT_SECONDS,
        max_retries=settings.AI_MAX_RETRIES,
        backoff_base=settings.AI_BACKOFF_BASE
    )

async def enrich_request_with_ai(req: StrategyRequest) -> StrategyRequest:
    """
    TASK-046: Implementare ai/request_enricher.py
    """
    if not req.free_text or not req.free_text.strip():
        return req
    
    system_prompt = (
        "Sei un assistente esperto di trading algoritmico. "
        "Dato il testo dell'utente, estrai i simboli di trading (es. BTC/USDT) e "
        "identifica il template di strategia più adatto tra: "
        "trend_ema, trend_ema_fast, mean_reversion_rsi, mean_reversion_rsi_aggressive, "
        "breakout_bb, breakout_bb_tight, momentum_macd, scalp_short_term. "
        "Rispondi SOLO con un oggetto JSON valido con chiavi 'symbols' (lista di stringhe) e 'template' (stringa)."
    )
    
    user_prompt = f"Testo utente: {req.free_text}\nAsset class: {req.asset_class}"
    
    client = get_model_client()
    try:
        response = await client.call_with_fallback(system_prompt, user_prompt)
        # Pulizia base se l'AI include markdown
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
            
        data = json.loads(content)
        
        # Aggiorniamo i simboli se trovati
        extracted_symbols = data.get("symbols", [])
        if extracted_symbols:
            # Assicuriamoci che i simboli abbiano il formato corretto (es. BTCUSDT -> BTC/USDT)
            # Per semplicità ora assumiamo che siano già validi o li passiamo così
            if not req.symbols:
                req.symbols = extracted_symbols
            else:
                # Uniamo i simboli se l'utente ne ha già messi alcuni
                req.symbols = list(set(req.symbols + extracted_symbols))
                
        # Potremmo usare il template per filtrare in futuro, per ora lo logghiamo
        logger.info(f"AI suggested template: {data.get('template')}")
        
    except (AllModelsUnavailableError, json.JSONDecodeError, Exception) as e:
        logger.error(f"AI enrichment failed: {e}")
        # TASK-045: Graceful degradation - restituiamo l'input invariato
        pass
        
    return req
