import importlib
import inspect
import logging
from typing import Callable, Dict, Any, Optional

logger = logging.getLogger(__name__)

class StrategyRegistry:
    _instance = None
    _strategies: Dict[str, Callable] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StrategyRegistry, cls).__new__(cls)
            cls._instance._load_defaults()
            cls._instance._load_plugins()
        return cls._instance

    def _load_defaults(self):
        """Carica gli indicatori core predefiniti."""
        from app.core.indicators import signal_ema_crossover, signal_rsi_reversion, signal_breakout_bb
        
        self.register("trend_ema", lambda df, p: signal_ema_crossover(df, p["ema_fast"], p["ema_slow"]))
        self.register("mean_reversion_rsi", lambda df, p: signal_rsi_reversion(
            df, p["rsi_period"], p["rsi_oversold"], p["rsi_overbought"]
        ))
        self.register("breakout_bb", lambda df, p: signal_breakout_bb(df, p["bb_period"], p["bb_std"]))

    def _load_plugins(self):
        """Carica plugin configurati nei settings."""
        try:
            from app.config import settings
            for plugin_module in settings.strategy_plugins_list:
                self.load_from_module(plugin_module)
        except ImportError:
            # Potrebbe succedere durante i test se settings non è disponibile
            pass

    def register(self, name: str, func: Callable):
        """Registra una funzione di segnale con un nome."""
        self._strategies[name] = func
        logger.info(f"Registered strategy: {name}")

    def get(self, name: str) -> Optional[Callable]:
        """Recupera una funzione di segnale per nome."""
        return self._strategies.get(name)

    def load_from_module(self, module_path: str):
        """
        Carica dinamicamente le funzioni da un modulo.
        Registra tutte le funzioni che iniziano con 'signal_'.
        Esempio: 'signal_custom' verrà registrata come 'custom'.
        """
        try:
            module = importlib.import_module(module_path)
            # Reload module to ensure we get latest changes (useful for hot-swap if needed)
            importlib.reload(module)
            
            for name, obj in inspect.getmembers(module):
                if inspect.isfunction(obj) and name.startswith("signal_"):
                    strat_name = name[7:]  # Rimuove 'signal_'
                    self.register(strat_name, obj)
                    
        except ImportError as e:
            logger.error(f"Could not load plugin module {module_path}: {e}")
        except Exception as e:
            logger.error(f"Error loading plugins from {module_path}: {e}")

    def list_strategies(self) -> list[str]:
        """Restituisce la lista dei nomi delle strategie registrate."""
        return list(self._strategies.keys())

# Singleton instance
registry = StrategyRegistry()
