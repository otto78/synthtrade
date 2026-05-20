"""
TASK-NOME-STRATEGIA: Genera nomi simpatici per le strategie usando l'AI.

Usa il ModelClient già esistente per chiamare l'AI via OpenRouter.
Il fallback usa nomi predefiniti se l'AI non risponde.
"""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Nomi di fallback strutturati per tema (usati se l'AI non risponde)
FALLBACK_ADJECTIVES = [
    "Audace", "Saggio", "Feroce", "Veloce", "Astuto", "Calmo",
    "Tenace", "Lesto", "Acuto", "Subdolo", "Mirabolante", "Fulmineo",
    "Silenzioso", "Preciso", "Instancabile", "Impavido",
]
FALLBACK_NOUNS = [
    "Lupo", "Falco", "Squalo", "Volpe", "Orso", "Aquila",
    "Toro", "Lince", "Fenice", "Cobra", "Pantera", "Ghepardo",
    "Lama", "Saggio", "Navigatore", "Cacciatore",
]


async def generate_funny_name(
    model_client,  # ModelClient instance
    template: str,
    pair: str,
    timeframe: str,
    params: dict,
    used_names: set[str] | None = None,
    variant_index: int = 0,
) -> str:
    """Genera un nome simpatico unico per la strategia usando l'AI.

    Args:
        model_client: Istanza di ModelClient configurata.
        template: Nome del template (es. trend_ema, breakout_bb).
        pair: Coppia di trading (es. BTC/USDT).
        timeframe: Timeframe (es. 1h, 4h).
        params: Parametri della strategia.
        used_names: Set di nomi già usati per evitare duplicati.
        variant_index: Indice della variante per generare nomi diversi.

    Returns:
        Nome simpatico generato dall'AI, o fallback se l'AI non risponde.
    """
    symbol = pair.split("/")[0]

    system_prompt = (
        "Sei un creativo specializzato in naming per strategie di trading algoritmico. "
        "Il tuo compito è generare un nome simpatico, originale e memorabile per ogni strategia.\n\n"
        "REGOLE:\n"
        "- MAX 6 parole, in italiano\n"
        "- Deve essere unico e non banale (niente 'La Strategia' o 'Il Trader')\n"
        "- Puoi usare metafore, giochi di parole, personaggi, animali, figure mitologiche\n"
        "- NON usare mai il nome del template o del timeframe nel nome\n"
        "- Il nome deve essere accattivante e dare personalità alla strategia\n"
        "- Rispondi SOLO con il nome, senza spiegazioni, senza virgolette, senza prefissi"
    )

    user_prompt = (
        f"Genera un nome simpatico per questa strategia di trading:\n"
        f"- Template: {template}\n"
        f"- Simbolo: {symbol}\n"
        f"- Timeframe: {timeframe}\n"
        f"- Parametri: {json.dumps(params, ensure_ascii=False)}\n\n"
        f"Esempi di stile: 'Il Drago di {symbol}', '{symbol} Selvaggia', "
        f"'L'Alchimista Quantico', 'Zorro Volante', 'La Mantide', 'Re {symbol}'"
    )

    # Prima prova con AI
    try:
        response = await model_client.call_with_fallback(system_prompt, user_prompt)
        name = response.content.strip().strip('"').strip("'").strip('"').strip("'")
        if name.startswith("```"):
            name = name.split("\n")[-1] if "\n" in name else name.replace("```", "")
        name = name.strip()
        if len(name) > 60:
            name = name[:60]
        if name:
            # Se il nome è già usato, append un suffisso
            if used_names is not None and name in used_names:
                name = f"{name} #{variant_index + 1}"
            if used_names is not None:
                used_names.add(name)
            logger.info(f"AI generato nome simpatico: '{name}' per {template} {symbol}")
            return name
    except Exception as e:
        logger.warning(f"AI name generation fallita: {e}")

    # Fallback: usa anche params nell'hash per varietà
    return _fallback_name(template, symbol, params, variant_index, used_names)


def _fallback_name(
    template: str,
    symbol: str,
    params: dict | None = None,
    variant_index: int = 0,
    used_names: set[str] | None = None,
) -> str:
    """Genera un nome di fallback vario, incorporando params e indice per unicità."""
    import hashlib
    import json
    # Usa params + indice per garantire nomi diversi anche su stesso template+symbol
    params_str = json.dumps(params, sort_keys=True) if params else str(variant_index)
    seed = f"{template}-{symbol}-{params_str}-{variant_index}"
    hash_val = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    adj_idx = hash_val % len(FALLBACK_ADJECTIVES)
    noun_idx = (hash_val // len(FALLBACK_ADJECTIVES)) % len(FALLBACK_NOUNS)

    # Combina più combinazioni possibili ruotando per lo stesso seed
    alt_adj = (adj_idx + variant_index) % len(FALLBACK_ADJECTIVES)
    alt_noun = (noun_idx + variant_index + 1) % len(FALLBACK_NOUNS)

    name = f"{FALLBACK_ADJECTIVES[adj_idx]} {FALLBACK_NOUNS[noun_idx]} di {symbol}"

    # Se il nome è già usato, usa la combinazione alternativa
    if used_names is not None and name in used_names:
        name = f"{FALLBACK_ADJECTIVES[alt_adj]} {FALLBACK_NOUNS[alt_noun]} di {symbol}"

    if used_names is not None:
        used_names.add(name)
    return name
