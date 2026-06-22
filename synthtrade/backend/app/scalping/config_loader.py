"""ScalpingConfigLoader — merge .env + DB runtime config.

Gerarchia (priorità crescente):
  1. Valori hardcoded come default di classe
  2. Valori da .env / config.py (settings)
  3. Valori da DB scalping_runtime_config (override runtime)

Il loader viene istanziato UNA volta all'avvio sessione e può essere
ricaricato on-demand via reload() senza restart del backend.
"""

import logging
from typing import Any
from app.config import settings
from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)


class ScalpingConfigLoader:
    """Configurazione scalping con override runtime da DB."""

    def __init__(self):
        self._config: dict[str, Any] = {}
        self._load()

    def _load(self):
        """Carica config: prima da settings (.env), poi override da DB."""
        # Step 1: valori base da settings (sottoclasse scalping)
        base = {
            "SCALPING_TRADE_VALUE":                  settings.scalping.SCALPING_TRADE_VALUE,
            "SCALPING_MAX_DAILY_LOSS":               settings.scalping.SCALPING_MAX_DAILY_LOSS,
            "SCALPING_MAX_DRAWDOWN_PCT":             settings.scalping.SCALPING_MAX_DRAWDOWN_PCT,
            "SCALPING_STOP_LOSS_PCT":                settings.scalping.SCALPING_STOP_LOSS_PCT,
            "SCALPING_TAKE_PROFIT_PCT":              settings.scalping.SCALPING_TAKE_PROFIT_PCT,
            "SCALPING_SIGNAL_STRENGTH_THRESHOLD":    settings.scalping.SCALPING_SIGNAL_STRENGTH_THRESHOLD,
            "SCALPING_MIN_CONFIDENCE":               settings.scalping.SCALPING_MIN_CONFIDENCE,
            "SCALPING_MIN_COLLECTORS":               settings.scalping.SCALPING_MIN_COLLECTORS,
            "SCALPING_SUPERVISOR_INTERVAL_SEC":      settings.scalping.SCALPING_SUPERVISOR_INTERVAL_SEC,
            "SCALPING_STRATEGY_COOLDOWN_SEC":        settings.scalping.SCALPING_STRATEGY_COOLDOWN_SEC,
            "SCALPING_PARAM_UPDATE_COOLDOWN_SEC":    settings.scalping.SCALPING_PARAM_UPDATE_COOLDOWN_SEC,
            "SCALPING_SUPERVISOR_MIN_TRADES_BEFORE_CHANGE": settings.scalping.SCALPING_SUPERVISOR_MIN_TRADES_BEFORE_CHANGE,
            "SCALPING_SUPERVISOR_MAX_REPEAT_DECISIONS": settings.scalping.SCALPING_SUPERVISOR_MAX_REPEAT_DECISIONS,
            "SCALPING_REGIME_TREND_THRESHOLD_PCT":   settings.scalping.SCALPING_REGIME_TREND_THRESHOLD_PCT,
            "SCALPING_REGIME_VOLATILE_THRESHOLD":    settings.scalping.SCALPING_REGIME_VOLATILE_THRESHOLD,
            "SCALPING_TA_VOLUME_ANOMALY_MULTIPLIER": settings.scalping.SCALPING_TA_VOLUME_ANOMALY_MULTIPLIER,
        }
        self._config = base

        # Step 2: override da DB
        try:
            db = get_supabase()
            rows = db.table("scalping_runtime_config").select("key, value, value_type").execute()
            if rows.data:
                type_map = {"float": float, "int": int, "bool": lambda v: v.lower() == "true", "str": str}
                for row in rows.data:
                    key = row["key"]
                    if key in self._config:
                        converter = type_map.get(row["value_type"], str)
                        try:
                            self._config[key] = converter(row["value"])
                        except (ValueError, TypeError) as e:
                            logger.warning("Config DB: valore non valido per %s=%s: %s", key, row["value"], e)
                logger.info("ScalpingConfigLoader: %d override DB caricati", len(rows.data))
        except Exception as e:
            logger.warning("ScalpingConfigLoader: DB non raggiungibile, uso solo .env: %s", e)

    def reload(self):
        """Ricarica la config da DB senza restart. Chiamare da API /config/reload."""
        logger.info("ScalpingConfigLoader: reload richiesto")
        self._load()

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    # Shortcut con tipo corretto
    @property
    def trade_value(self) -> float:
        return self._config["SCALPING_TRADE_VALUE"]

    @property
    def signal_strength_threshold(self) -> float:
        return self._config["SCALPING_SIGNAL_STRENGTH_THRESHOLD"]

    @property
    def min_confidence(self) -> float:
        return self._config["SCALPING_MIN_CONFIDENCE"]

    @property
    def min_collectors(self) -> int:
        return self._config["SCALPING_MIN_COLLECTORS"]

    @property
    def supervisor_interval_sec(self) -> int:
        return self._config["SCALPING_SUPERVISOR_INTERVAL_SEC"]

    @property
    def strategy_cooldown_sec(self) -> int:
        return self._config["SCALPING_STRATEGY_COOLDOWN_SEC"]

    @property
    def supervisor_min_trades_before_change(self) -> int:
        return self._config["SCALPING_SUPERVISOR_MIN_TRADES_BEFORE_CHANGE"]

    @property
    def supervisor_max_repeat_decisions(self) -> int:
        return self._config["SCALPING_SUPERVISOR_MAX_REPEAT_DECISIONS"]

    @property
    def stop_loss_pct(self) -> float:
        return self._config["SCALPING_STOP_LOSS_PCT"]

    @property
    def take_profit_pct(self) -> float:
        return self._config["SCALPING_TAKE_PROFIT_PCT"]

    @property
    def max_daily_loss(self) -> float:
        return self._config["SCALPING_MAX_DAILY_LOSS"]

    @property
    def regime_trend_threshold_pct(self) -> float:
        return self._config["SCALPING_REGIME_TREND_THRESHOLD_PCT"]

    @property
    def regime_volatile_threshold(self) -> float:
        return self._config["SCALPING_REGIME_VOLATILE_THRESHOLD"]

    @property
    def ta_volume_anomaly_multiplier(self) -> float:
        return self._config["SCALPING_TA_VOLUME_ANOMALY_MULTIPLIER"]


# Singleton — istanziato all'avvio, condiviso da tutti i moduli scalping
_scalping_config: ScalpingConfigLoader | None = None


def get_scalping_config() -> ScalpingConfigLoader:
    global _scalping_config
    if _scalping_config is None:
        _scalping_config = ScalpingConfigLoader()
    return _scalping_config
