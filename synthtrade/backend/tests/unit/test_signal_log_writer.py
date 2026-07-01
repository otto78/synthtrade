"""Test unitari per Signal Log Writer."""

import pytest
from unittest.mock import Mock, patch
from app.core.signal_log_writer import (
    log_signal_decision,
    log_pipeline_decision,
    log_block_decision,
    log_mean_reversion_decision,
    log_hold_decision,
    log_execution_error,
    log_rejected_short_unsupported
)


@pytest.fixture
def mock_supabase():
    """Mock client Supabase."""
    mock = Mock()
    mock.table.return_value.insert.return_value.execute.return_value.data = [{"id": "test-id"}]
    return mock


class TestLogSignalDecision:
    """Test per log_signal_decision."""
    
    @patch('app.core.signal_log_writer.get_supabase')
    def test_log_signal_decision_success(self, mock_get_supabase, mock_supabase):
        """Test logging decisione con successo."""
        mock_get_supabase.return_value = mock_supabase
        
        result = log_signal_decision(
            session_id="123",
            symbol="BTCUSDT",
            decision_type="execute",
            regime="ranging",
            strategy_type="rsi_bollinger"
        )
        
        assert result == "test-id"  # log_signal_decision restituisce UUID
        mock_supabase.table.assert_called_once_with("session_signal_log")
    
    @patch('app.core.signal_log_writer.get_supabase')
    def test_log_signal_decision_with_reason(self, mock_get_supabase, mock_supabase):
        """Test logging decisione con motivo."""
        mock_get_supabase.return_value = mock_supabase
        
        result = log_signal_decision(
            session_id="123",
            symbol="BTCUSDT",
            decision_type="execute",
            decision_reason="Tutti i criteri soddisfatti",
            regime="ranging",
            strategy_type="rsi_bollinger"
        )
        
        assert result == "test-id"  # log_signal_decision restituisce UUID
    
    @patch('app.core.signal_log_writer.get_supabase')
    def test_log_signal_decision_error(self, mock_get_supabase):
        """Test logging decisione con errore (non-blocking)."""
        mock_get_supabase.side_effect = Exception("DB error")
        
        result = log_signal_decision(
            session_id="123",
            symbol="BTCUSDT",
            decision_type="execute",
            regime="ranging",
            strategy_type="rsi_bollinger"
        )
        
        assert result is None  # non-blocking, ritorna None su errore
    
    @patch('app.core.signal_log_writer.get_supabase')
    def test_log_signal_decision_full_context(self, mock_get_supabase, mock_supabase):
        """Test logging con contesto completo."""
        mock_get_supabase.return_value = mock_supabase
        
        result = log_signal_decision(
            session_id="123",
            symbol="BTCUSDT",
            decision_type="execute",
            regime="ranging",
            strategy_type="rsi_bollinger",
            tech_signal="BUY",
            tech_confidence=0.85,
            intel_score=0.75,
            intel_bias="bullish",
            trend_direction="converging",
            trend_value=0.5
        )
        
        assert result == "test-id"  # log_signal_decision restituisce UUID
    
    def test_log_signal_decision_missing_required(self):
        """Test che manca campo obbligatorio ritorna None (non-blocking)."""
        result = log_signal_decision(
            session_id="123",
            symbol="BTCUSDT",
            decision_type="execute"
            # regime e strategy_type mancanti
        )
        
        assert result is None  # non-blocking, ritorna None invece di crash


class TestLogPipelineDecision:
    """Test per log_pipeline_decision."""
    
    @patch('app.core.signal_log_writer.get_supabase')
    def test_log_pipeline_decision_execute(self, mock_get_supabase, mock_supabase):
        """Test logging decisione PIPELINE con tradeable=True."""
        mock_get_supabase.return_value = mock_supabase
        
        result = log_pipeline_decision(
            session_id="123",
            symbol="BTCUSDT",
            regime="ranging",
            strategy_type="rsi_bollinger",
            tradeable=True
        )
        
        assert result is True  # Restituisce bool per compatibilità
    
    @patch('app.core.signal_log_writer.get_supabase')
    def test_log_pipeline_decision_rejected(self, mock_get_supabase, mock_supabase):
        """Test logging decisione PIPELINE con tradeable=False."""
        mock_get_supabase.return_value = mock_supabase
        
        result = log_pipeline_decision(
            session_id="123",
            symbol="BTCUSDT",
            regime="ranging",
            strategy_type="rsi_bollinger",
            tradeable=False
        )
        
        assert result is True  # Restituisce bool per compatibilità
    
    @patch('app.core.signal_log_writer.get_supabase')
    def test_log_pipeline_decision_with_vol_anomaly(self, mock_get_supabase, mock_supabase):
        """Test logging decisione PIPELINE con vol_anomaly."""
        mock_get_supabase.return_value = mock_supabase
        
        result = log_pipeline_decision(
            session_id="123",
            symbol="BTCUSDT",
            regime="ranging",
            strategy_type="rsi_bollinger",
            tradeable=True,
            vol_anomaly=True
        )
        
        assert result is True  # Restituisce bool per compatibilità


class TestLogBlockDecision:
    """Test per log_block_decision."""
    
    @patch('app.core.signal_log_writer.get_supabase')
    def test_log_block_decision(self, mock_get_supabase, mock_supabase):
        """Test logging decisione BLOCK."""
        mock_get_supabase.return_value = mock_supabase
        
        result = log_block_decision(
            session_id="123",
            symbol="BTCUSDT",
            block_reason="conflitto intelligence-tecnico",
            regime="ranging",
            strategy_type="rsi_bollinger"
        )
        
        assert result is True  # Restituisce bool per compatibilità


class TestLogMeanReversionDecision:
    """Test per log_mean_reversion_decision."""
    
    @patch('app.core.signal_log_writer.get_supabase')
    def test_log_mean_reversion_decision(self, mock_get_supabase, mock_supabase):
        """Test logging decisione MEAN-REVERSION."""
        mock_get_supabase.return_value = mock_supabase
        
        result = log_mean_reversion_decision(
            session_id="123",
            symbol="BTCUSDT",
            override_reason="permesso nonostante bias=bearish",
            regime="ranging",
            strategy_type="rsi_bollinger"
        )
        
        assert result is True  # Restituisce bool per compatibilità


class TestLogHoldDecision:
    """Test per log_hold_decision."""
    
    @patch('app.core.signal_log_writer.get_supabase')
    def test_log_hold_decision(self, mock_get_supabase, mock_supabase):
        """Test logging decisione HOLD."""
        mock_get_supabase.return_value = mock_supabase
        
        result = log_hold_decision(
            session_id="123",
            symbol="BTCUSDT",
            hold_reason="existing BUY position matches BUY signal",
            regime="ranging",
            strategy_type="rsi_bollinger"
        )
        
        assert result is True  # Restituisce bool per compatibilità


class TestLogExecutionError:
    """Test per log_execution_error."""
    
    @patch('app.core.signal_log_writer.get_supabase')
    def test_log_execution_error(self, mock_get_supabase, mock_supabase):
        """Test logging errore esecuzione."""
        mock_get_supabase.return_value = mock_supabase
        
        result = log_execution_error(
            session_id="123",
            symbol="BTCUSDT",
            error_message="insufficient balance",
            regime="ranging",
            strategy_type="rsi_bollinger"
        )
        
        assert result is True  # Restituisce bool per compatibilità


class TestLogRejectedShortUnsupported:
    """Test per log_rejected_short_unsupported."""
    
    @patch('app.core.signal_log_writer.get_supabase')
    def test_log_rejected_short_unsupported(self, mock_get_supabase, mock_supabase):
        """Test logging rifiuto short non supportato."""
        mock_get_supabase.return_value = mock_supabase
        
        result = log_rejected_short_unsupported(
            session_id="123",
            symbol="BTCUSDT",
            regime="ranging",
            strategy_type="rsi_bollinger"
        )
        
        assert result is True  # Restituisce bool per compatibilità  # Restituisce bool per compatibilità con altre funzioni