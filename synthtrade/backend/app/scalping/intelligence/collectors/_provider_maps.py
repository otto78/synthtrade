"""Provider-aware perpetual mappings for intelligence collectors (TASK-1153).

Funding rate / Open Interest exist ONLY on USDT perpetual futures (SWAP) on OKX.
The perpetual is quoted in USDT, NOT in EUR, so these data reflect sentiment on the
base asset (BTC/ETH) and are used as a PROXY for the EUR pair — documented as such,
never presented as literal BTC-EUR data.

Single source of truth shared by the intelligence collectors and OkxExchangeAdapter.
"""

# base asset -> OKX SWAP instId (or None if no perpetual exists on any exchange)
OKX_PERPETUAL_MAP: dict[str, str | None] = {
    "BTC": "BTC-USDT-SWAP",
    "ETH": "ETH-USDT-SWAP",
    "OKB": None,  # no perpetual on any exchange
}


def extract_base_asset(symbol: str) -> str:
    """Extract the base asset from a symbol of any format.

    Examples:
        "BTC-EUR" -> "BTC"
        "BTCUSDT" -> "BTC"
        "BTCUSDC" -> "BTC"
        "OKB-EUR" -> "OKB"
        "ETH-USDT" -> "ETH"
    """
    s = symbol.upper().replace("-", "").replace("/", "")
    for quote in ("USDT", "USDC", "EUR", "USD"):
        if s.endswith(quote):
            return s[: -len(quote)]
    return s
