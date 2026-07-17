import logging
import time
from typing import Dict, Any

from app.scalping._state import (
    _execution_state,
    _last_warning,
    _warning_throttle_sec,
    _bnb_price_cache,
    _bnb_price_cache_ttl,
)

logger = logging.getLogger(__name__)


def _throttled_warning(msg: str, key: str = "") -> None:
    """Emette un warning solo se non è già stato emesso negli ultimi N secondi."""
    now = time.time()
    throttle_key = key or msg[:80]
    last = _last_warning.get(throttle_key, 0.0)
    if now - last >= _warning_throttle_sec:
        logger.warning(msg)
        _last_warning[throttle_key] = now
    else:
        logger.debug(f"[THROTTLED] {msg}")


def _get_fee_rate(fee_tier, rate_type: str, default: float = 0.001) -> float:
    """Helper to get fee rate from either dict or FeeTier dataclass."""
    if isinstance(fee_tier, dict):
        return fee_tier.get(rate_type, default)
    else:
        return getattr(fee_tier, rate_type, default)


def _is_valid_uuid(value: str) -> bool:
    """Return True if value is a valid UUID string."""
    import re
    return bool(re.match(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        str(value).lower()
    ))


def _exit_price_ratio(net_pct: float, entry_fee_rate: float, exit_fee_rate: float) -> float:
    """Rapporto prezzo_uscita/prezzo_entrata per un target netto net_pct (%).

    Modello round-trip (long): net = (1-fe)*ratio*(1-fx) - 1
    => ratio = (1 + net/100) / ((1-fe)*(1-fx))
    """
    return (1 + net_pct / 100) / ((1 - entry_fee_rate) * (1 - exit_fee_rate))


def _net_to_gross_pct(net_pct: float, entry_fee_rate: float, exit_fee_rate: float) -> float:
    """Converte un target NETTO (%) nel movimento di prezzo LORDO (%) necessario
    perché, dopo le due fee (entry + exit), il risultato netto coincida col target.
    """
    return (_exit_price_ratio(net_pct, entry_fee_rate, exit_fee_rate) - 1) * 100


def _round_trip_fee_drag_pct(entry_fee_rate: float, exit_fee_rate: float) -> float:
    """Perdita netta % vendendo allo stesso prezzo di acquisto (solo fee)."""
    return (1 - (1 - entry_fee_rate) * (1 - exit_fee_rate)) * 100


def _expected_net_pct_at_exit(
    entry: float,
    exit_price: float,
    side: str,
    entry_fee_rate: float,
    exit_fee_rate: float,
) -> float:
    """Rendimento netto % sul capitale deployato dopo entry+exit fee."""
    if entry <= 0 or exit_price <= 0:
        return 0.0
    if side.upper() == "BUY":
        ratio = exit_price / entry
    else:
        ratio = entry / exit_price
    return ((1 - entry_fee_rate) * ratio * (1 - exit_fee_rate) - 1) * 100


def _tp_price_from_entry(
    entry: float,
    side: str,
    net_tp_pct: float,
    entry_fee_rate: float,
    exit_fee_rate: float,
    *,
    price_prec: int | None = None,
) -> float:
    """Prezzo TP: sopra entry per BUY/long, sotto entry per SELL/short."""
    ratio = _exit_price_ratio(net_tp_pct, entry_fee_rate, exit_fee_rate)
    price = entry * ratio if side.upper() == "BUY" else entry / ratio
    return round(price, price_prec) if price_prec is not None else price


def _sl_gross_fraction(net_sl_pct: float, entry_fee_rate: float, exit_fee_rate: float) -> float:
    """Calcola la frazione di movimento lordo (positiva) necessaria per ottenere
    un target netto -net_sl_pct dopo le fee. Wrappa abs(_net_to_gross_pct()) / 100
    per garantire che il risultato sia sempre positivo.
    """
    return abs(_net_to_gross_pct(net_sl_pct, entry_fee_rate, exit_fee_rate)) / 100


def _sl_price_from_entry(
    entry: float,
    side: str,
    net_sl_pct: float,
    entry_fee_rate: float,
    exit_fee_rate: float,
    *,
    price_prec: int | None = None,
) -> tuple[float, bool]:
    """Prezzo SL con target netto -net_sl_pct % sul capitale.

    Returns (price, feasible). Per long, se fee round-trip > target SL netto,
    il prezzo ideale cadrebbe sopra entry (infeasible su exchange): si clamp
    appena sotto entry e feasible=False.
    """
    net_sl_pct = abs(net_sl_pct)
    ratio = _exit_price_ratio(-net_sl_pct, entry_fee_rate, exit_fee_rate)
    feasible = True
    min_frac = max(net_sl_pct / 100, 1e-4)

    if side.upper() == "BUY":
        if ratio >= 1.0:
            ratio = 1.0 - min_frac
            feasible = False
        price = entry * ratio
    else:
        if ratio >= 1.0:
            price = entry * (1 + min_frac)
            feasible = False
        else:
            price = entry / ratio
    if price_prec is not None:
        price = round(price, price_prec)
    return price, feasible


async def _convert_bnb_commission_to_usdc(exchange, bnb_amount: float, context: str = "") -> float:
    """Convert BNB commission to USDC using exchange ticker price.

    Uses a local cache (60s TTL) to minimize API calls.
    Falls back to last known cached price if fetch fails, then to fee-tier estimate.
    Log throttling prevents flood of identical warnings during rate limiting.
    """
    now = time.time()

    # Try to fetch fresh price (get_ticker_price has its own 15s cache)
    bnb_price = None
    try:
        bnb_price = await exchange.get_ticker_price("BNBUSDC")
        _bnb_price_cache["price"] = bnb_price
        _bnb_price_cache["timestamp"] = now
    except Exception as e:
        # Use local cache if available (60s TTL)
        if now - _bnb_price_cache["timestamp"] < _bnb_price_cache_ttl and _bnb_price_cache["price"] > 0:
            bnb_price = _bnb_price_cache["price"]
            _throttled_warning(
                f"{context}failed to fetch BNB price: {e} — using cached price ({bnb_price})",
                key=f"bnb_price_fetch_{context}"
            )
        else:
            _throttled_warning(
                f"{context}failed to convert {bnb_amount} BNB to USDC: {e} — using fee-tier estimate",
                key=f"bnb_conv_fail_{context}"
            )

    if bnb_price is not None and bnb_price > 0:
        usdc_value = bnb_amount * bnb_price
        logger.debug(f"{context}converted {bnb_amount} BNB to {usdc_value:.4f} USDC @ {bnb_price}")
        return usdc_value

    # Ultimate fallback: fee-tier estimate
    fee_tier = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
    entry_fee_rate = _get_fee_rate(fee_tier, "taker", 0.001)
    entry_val = float(_execution_state.get("session", {}).get("live_balance", 0))
    return entry_val * entry_fee_rate if entry_val > 0 else 0.0
