"""Test unitari per LogPersistenceLayer."""

import pytest
from pathlib import Path
from app.core.log_persistence import LogStorage, LogParser, LogContent


@pytest.fixture
def sample_log_content():
    """Contenuto log di esempio per i test."""
    return """SESSION LOG DUMP
Session ID: test-session-123
Symbol: BTCUSDT
Generated: 2026-06-29 12:00:00

[2026-06-29 12:00:00] PIPELINE: regime=ranging strategy=rsi_bollinger vol_anomaly=True tradeable=True
[2026-06-29 12:00:01] 🟢 SIGNAL: BUY confidence=0.85
[2026-06-29 12:00:02] DECISION APPROVED
[2026-06-29 12:00:03] >>> TRADE: side=BUY
[2026-06-29 12:00:04] Intel snapshot score=0.75 bias=bullish
[2026-06-29 12:00:05] BLOCK: conflitto intelligence-tecnico (divergence too high)
"""


class TestLogStorage:
    """Test per LogStorage."""
    
    def test_persist_to_file(self, tmp_path):
        """Test salvataggio su filesystem."""
        storage = LogStorage()
        test_path = tmp_path / "test_session.log"
        
        result = storage.persist_to_file("test content", str(test_path))
        
        assert result is True
        assert test_path.exists()
        assert test_path.read_text() == "test content"
    
    def test_persist_to_file_creates_directory(self, tmp_path):
        """Test che persist_to_file crei directory se non esiste."""
        storage = LogStorage()
        test_path = tmp_path / "subdir" / "nested" / "test.log"
        
        result = storage.persist_to_file("test content", str(test_path))
        
        assert result is True
        assert test_path.exists()
    
    def test_load_from_file(self, tmp_path):
        """Test caricamento da filesystem."""
        storage = LogStorage()
        test_path = tmp_path / "test_session.log"
        test_path.write_text("test content")
        
        log_content = storage.load_from_file(str(test_path))
        
        assert log_content is not None
        assert log_content.content == "test content"
        assert log_content.source == 'file'
        assert log_content.session_id == "test_session"
    
    def test_load_from_file_not_found(self, tmp_path):
        """Test caricamento file inesistente."""
        storage = LogStorage()
        test_path = tmp_path / "nonexistent.log"
        
        log_content = storage.load_from_file(str(test_path))
        
        assert log_content is None
    
    def test_persist_to_db_without_client(self):
        """Test salvataggio DB senza client configurato."""
        storage = LogStorage()
        
        result = storage.persist_to_db("session-123", "content")
        
        assert result is False
    
    def test_load_from_db_without_client(self):
        """Test caricamento DB senza client configurato."""
        storage = LogStorage()
        
        log_content = storage.load_from_db("session-123")
        
        assert log_content is None


class TestLogParser:
    """Test per LogParser."""
    
    def test_parse_lines_to_records(self, sample_log_content):
        """Test parsing linee in record strutturati."""
        parser = LogParser()
        records = parser.parse_lines_to_records(sample_log_content)
        
        assert len(records) > 0
        assert any('regime' in record for record in records)
        assert any('strategy' in record for record in records)
    
    def test_parse_to_structured_data(self, sample_log_content):
        """Test parsing in dati aggregati."""
        parser = LogParser()
        analysis = parser.parse_to_structured_data(sample_log_content)
        
        assert 'decisions' in analysis
        assert 'signals' in analysis
        assert 'trades' in analysis
        assert 'regime_changes' in analysis
        assert 'strategies_used' in analysis
    
    def test_parse_to_structured_data_counts(self, sample_log_content):
        """Test che i conteggi siano corretti."""
        parser = LogParser()
        analysis = parser.parse_to_structured_data(sample_log_content)
        
        assert analysis['decisions']['approved'] > 0
        assert analysis['signals']['buy'] > 0
        assert analysis['trades']['buy'] > 0
        assert 'ranging' in analysis['regime_changes']
        assert 'rsi_bollinger' in analysis['strategies_used']
    
    def test_extract_pipeline_context_success(self):
        """Test estrazione contesto da linea PIPELINE."""
        parser = LogParser()
        log_line = "PIPELINE: regime=ranging strategy=rsi_bollinger vol_anomaly=True tradeable=True"
        
        context = parser.extract_pipeline_context(log_line)
        
        assert context is not None
        assert context['regime'] == 'ranging'
        assert context['strategy'] == 'rsi_bollinger'
        assert context['vol_anomaly'] is True
        assert context['tradeable'] is True
    
    def test_extract_pipeline_context_not_pipeline(self):
        """Test estrazione contesto da linea non PIPELINE."""
        parser = LogParser()
        log_line = "Regular log message without PIPELINE"
        
        context = parser.extract_pipeline_context(log_line)
        
        assert context is None
    
    def test_extract_pipeline_context_minimal(self):
        """Test estrazione contesto PIPELINE con campi minimi."""
        parser = LogParser()
        log_line = "PIPELINE: regime=trending_up strategy=ema_cross"
        
        context = parser.extract_pipeline_context(log_line)
        
        assert context is not None
        assert context['regime'] == 'trending_up'
        assert context['strategy'] == 'ema_cross'
        assert context['vol_anomaly'] is False
        assert context['tradeable'] is False
    
    def test_parse_empty_content(self):
        """Test parsing contenuto vuoto."""
        parser = LogParser()
        analysis = parser.parse_to_structured_data("")
        
        # split('\n') su stringa vuota restituisce [''], quindi 1 linea
        assert analysis['total_lines'] == 1
        assert analysis['structured_records'] == 0
        assert analysis['decisions']['total'] == 0
    
    def test_parse_content_no_patterns(self):
        """Test parsing contenuto senza pattern riconosciuti."""
        parser = LogParser()
        content = "Random log messages\nWithout any patterns\nJust plain text"
        
        analysis = parser.parse_to_structured_data(content)
        
        assert analysis['structured_records'] == 0
        assert analysis['decisions']['total'] == 0
        assert analysis['signals']['total'] == 0


class TestLogContent:
    """Test per LogContent dataclass."""
    
    def test_log_content_creation(self):
        """Test creazione LogContent."""
        log_content = LogContent(
            session_id="test-123",
            content="test content",
            source='db',
            symbol="BTCUSDT"
        )
        
        assert log_content.session_id == "test-123"
        assert log_content.content == "test content"
        assert log_content.source == 'db'
        assert log_content.symbol == "BTCUSDT"
    
    def test_log_content_optional_fields(self):
        """Test LogContent con campi opzionali."""
        log_content = LogContent(
            session_id="test-123",
            content="test content",
            source='file'
        )
        
        assert log_content.symbol is None
        assert log_content.metadata is None