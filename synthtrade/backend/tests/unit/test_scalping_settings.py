"""TDD test per ScalpingSettings (TASK-800).

🔴 RED: scriviamo i test prima dell'implementazione.
🟢 GREEN: l'implementazione esiste già in config.py.
🔵 REFACTOR: verificheremo dopo.
"""
import os
import pytest
from app.config import ScalpingSettings, settings


class TestScalpingSettingsDefaults:
    """Verifica che i valori di default siano caricati correttamente."""

    def test_default_max_daily_loss_pct(self):
        """SCALPING_MAX_DAILY_LOSS_PCT default deve essere 3.0%"""
        sut = ScalpingSettings()
        assert sut.SCALPING_MAX_DAILY_LOSS_PCT == 3.0

    def test_default_max_consecutive_losses(self):
        """SCALPING_MAX_CONSECUTIVE_LOSSES default deve essere 5"""
        sut = ScalpingSettings()
        assert sut.SCALPING_MAX_CONSECUTIVE_LOSSES == 5

    def test_default_max_position_size(self):
        """SCALPING_MAX_POSITION_SIZE default deve essere 0.01"""
        sut = ScalpingSettings()
        assert sut.SCALPING_MAX_POSITION_SIZE == 0.01

    def test_default_timeframe(self):
        """SCALPING_TIMEFRAME default deve essere '1m'"""
        sut = ScalpingSettings()
        assert sut.SCALPING_TIMEFRAME == '1m'

    def test_default_signal_strength_threshold(self):
        """SCALPING_SIGNAL_STRENGTH_THRESHOLD default deve essere 30.0"""
        sut = ScalpingSettings()
        assert sut.SCALPING_SIGNAL_STRENGTH_THRESHOLD == 30.0

    def test_default_min_confidence(self):
        """SCALPING_MIN_CONFIDENCE default deve essere 0.6"""
        sut = ScalpingSettings()
        assert sut.SCALPING_MIN_CONFIDENCE == 0.6

    def test_default_execution_interval_ms(self):
        """SCALPING_EXECUTION_INTERVAL_MS default deve essere 500"""
        sut = ScalpingSettings()
        assert sut.SCALPING_EXECUTION_INTERVAL_MS == 500

    def test_default_candle_buffer_size(self):
        """SCALPING_CANDLE_BUFFER_SIZE default deve essere 100"""
        sut = ScalpingSettings()
        assert sut.SCALPING_CANDLE_BUFFER_SIZE == 100

    def test_default_intel_update_interval(self):
        """SCALPING_INTEL_UPDATE_INTERVAL_SEC default deve essere 60"""
        sut = ScalpingSettings()
        assert sut.SCALPING_INTEL_UPDATE_INTERVAL_SEC == 60

    def test_default_supervisor_interval(self):
        """SCALPING_SUPERVISOR_INTERVAL_MIN default deve essere 10"""
        sut = ScalpingSettings()
        assert sut.SCALPING_SUPERVISOR_INTERVAL_MIN == 10

    def test_default_supervisor_min_trades(self):
        """SCALPING_SUPERVISOR_MIN_TRADES_BEFORE_DECISION default deve essere 3"""
        sut = ScalpingSettings()
        assert sut.SCALPING_SUPERVISOR_MIN_TRADES_BEFORE_DECISION == 3

    def test_default_opportunity_poll_interval(self):
        """SCALPING_OPPORTUNITY_POLL_INTERVAL_MIN default deve essere 5"""
        sut = ScalpingSettings()
        assert sut.SCALPING_OPPORTUNITY_POLL_INTERVAL_MIN == 5

    def test_default_cryptopanic_key_empty(self):
        """CRYPTOPANIC_API_KEY default deve essere stringa vuota"""
        sut = ScalpingSettings()
        assert sut.CRYPTOPANIC_API_KEY == ''

    def test_default_scalping_mode(self):
        """SCALPING_DEFAULT_MODE default deve essere 'PAPER'"""
        sut = ScalpingSettings()
        assert sut.SCALPING_DEFAULT_MODE == 'PAPER'


class TestScalpingSettingsOverride:
    """Verifica che i valori possano essere sovrascritti via env var."""

    @pytest.fixture(autouse=True)
    def setup_env_vars(self):
        """Imposta env var di test prima di ogni test e le pulisce dopo."""
        self._env_backup = {}
        self._test_vars = {}
        yield
        # Pulizia: ripristina le var originali
        for key in self._test_vars:
            if key in self._env_backup and self._env_backup[key] is not None:
                os.environ[key] = self._env_backup[key]
            elif key in os.environ:
                del os.environ[key]

    def _set_env(self, key: str, value: str):
        """Imposta una env var salvando il backup."""
        self._env_backup[key] = os.environ.get(key)
        self._test_vars[key] = value
        os.environ[key] = value

    def test_override_max_daily_loss_pct(self):
        self._set_env('SCALPING_MAX_DAILY_LOSS_PCT', '5.0')
        sut = ScalpingSettings()
        assert sut.SCALPING_MAX_DAILY_LOSS_PCT == 5.0

    def test_override_max_consecutive_losses(self):
        self._set_env('SCALPING_MAX_CONSECUTIVE_LOSSES', '3')
        sut = ScalpingSettings()
        assert sut.SCALPING_MAX_CONSECUTIVE_LOSSES == 3

    def test_override_timeframe(self):
        self._set_env('SCALPING_TIMEFRAME', '5m')
        sut = ScalpingSettings()
        assert sut.SCALPING_TIMEFRAME == '5m'

    def test_override_signal_strength_threshold(self):
        self._set_env('SCALPING_SIGNAL_STRENGTH_THRESHOLD', '50.0')
        sut = ScalpingSettings()
        assert sut.SCALPING_SIGNAL_STRENGTH_THRESHOLD == 50.0

    def test_override_cryptopanic_key(self):
        self._set_env('CRYPTOPANIC_API_KEY', 'test_key_123')
        sut = ScalpingSettings()
        assert sut.CRYPTOPANIC_API_KEY == 'test_key_123'

    def test_override_scalping_mode(self):
        self._set_env('SCALPING_DEFAULT_MODE', 'LIVE')
        sut = ScalpingSettings()
        assert sut.SCALPING_DEFAULT_MODE == 'LIVE'


class TestScalpingSettingsTypeCoercion:
    """Verifica che i tipi siano corretti (es: float non stringa)."""

    def test_max_daily_loss_pct_is_float(self):
        sut = ScalpingSettings()
        assert isinstance(sut.SCALPING_MAX_DAILY_LOSS_PCT, float)

    def test_max_consecutive_losses_is_int(self):
        sut = ScalpingSettings()
        assert isinstance(sut.SCALPING_MAX_CONSECUTIVE_LOSSES, int)

    def test_execution_interval_ms_is_int(self):
        sut = ScalpingSettings()
        assert isinstance(sut.SCALPING_EXECUTION_INTERVAL_MS, int)

    def test_candle_buffer_size_is_int(self):
        sut = ScalpingSettings()
        assert isinstance(sut.SCALPING_CANDLE_BUFFER_SIZE, int)

    def test_min_confidence_is_float(self):
        sut = ScalpingSettings()
        assert isinstance(sut.SCALPING_MIN_CONFIDENCE, float)

    def test_timeframe_is_str(self):
        sut = ScalpingSettings()
        assert isinstance(sut.SCALPING_TIMEFRAME, str)

    def test_default_mode_is_str(self):
        sut = ScalpingSettings()
        assert isinstance(sut.SCALPING_DEFAULT_MODE, str)


class TestScalpingSettingsAccessViaSettings:
    """Verifica che settings.scalping funzioni correttamente."""

    def test_settings_scalping_is_scalpingsettings_instance(self):
        assert isinstance(settings.scalping, ScalpingSettings)

    def test_settings_scalping_returns_same_instance(self):
        """La property scalping deve essere cached (stessa istanza)."""
        assert settings.scalping is settings.scalping

    def test_settings_scalping_has_defaults(self):
        assert settings.scalping.SCALPING_MAX_DAILY_LOSS_PCT == 3.0
        assert settings.scalping.SCALPING_TIMEFRAME == '1m'
        assert settings.scalping.SCALPING_DEFAULT_MODE == 'PAPER'