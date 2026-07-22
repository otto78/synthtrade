"""Log Persistence Layer — astrazione per persistenza e parsing dei log.

Questo modulo fornisce:
- LogStorage: astrazione per persistenza su DB e filesystem
- LogParser: parsing dei log testuali per estrazione dati strutturati
- LogContent: dataclass per contenuto log normalizzato
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from pathlib import Path
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class LogContent:
    """Contenuto normalizzato di un log di sessione."""
    session_id: str
    content: str
    source: str  # 'db' o 'file'
    symbol: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LogStorage:
    """Astrazione per persistenza dei log su DB e filesystem."""
    
    def __init__(self, supabase_client=None):
        """Inizializza LogStorage.
        
        Args:
            supabase_client: Client Supabase per operazioni DB (opzionale)
        """
        self.supabase = supabase_client
    
    def persist_to_db(self, session_id: str, content: str, symbol: str = None) -> bool:
        """Salva il contenuto del log su DB.
        
        Args:
            session_id: ID della sessione
            content: Contenuto del log
            symbol: Simbolo trading (opzionale)
        
        Returns:
            True se salvato con successo, False altrimenti
        """
        if not self.supabase:
            logger.warning("Supabase client non configurato, impossibile salvare su DB")
            return False
        
        try:
            self.supabase.table("scalping_sessions").update({
                "log_content": content
            }).eq("id", session_id).execute()
            logger.info(f"Log salvato su DB per sessione {session_id}")
            return True
        except Exception as e:
            logger.error(f"Errore salvataggio log su DB: {e}")
            return False
    
    def persist_to_file(self, content: str, path: str) -> bool:
        """Salva il contenuto del log su filesystem.
        
        Args:
            content: Contenuto del log
            path: Percorso del file
        
        Returns:
            True se salvato con successo, False altrimenti
        """
        try:
            file_path = Path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding='utf-8')
            logger.info(f"Log salvato su filesystem: {path}")
            return True
        except Exception as e:
            logger.error(f"Errore salvataggio log su filesystem: {e}")
            return False
    
    def load_from_db(self, session_id: str) -> Optional[LogContent]:
        """Carica il contenuto del log dal DB.
        
        Args:
            session_id: ID della sessione
        
        Returns:
            LogContent se trovato, None altrimenti
        """
        if not self.supabase:
            logger.warning("Supabase client non configurato, impossibile caricare da DB")
            return None
        
        try:
            resp = self.supabase.table("scalping_sessions").select(
                "log_content, symbol"
            ).eq("id", session_id).limit(1).execute()
            
            if not resp.data:
                logger.warning(f"Nessun log trovato per sessione {session_id}")
                return None
            
            row = resp.data[0]
            log_content = row.get("log_content")
            if not log_content:
                logger.warning(f"Log content vuoto per sessione {session_id}")
                return None
            
            return LogContent(
                session_id=session_id,
                content=log_content,
                source='db',
                symbol=row.get("symbol")
            )
        except Exception as e:
            logger.error(f"Errore caricamento log da DB: {e}")
            return None
    
    def load_from_file(self, path: str) -> Optional[LogContent]:
        """Carica il contenuto del log dal filesystem.
        
        Args:
            path: Percorso del file
        
        Returns:
            LogContent se trovato, None altrimenti
        """
        try:
            file_path = Path(path)
            if not file_path.exists():
                logger.warning(f"File log non trovato: {path}")
                return None
            
            content = file_path.read_text(encoding='utf-8')
            return LogContent(
                session_id=file_path.stem,  # nome file senza estensione
                content=content,
                source='file'
            )
        except Exception as e:
            logger.error(f"Errore caricamento log da filesystem: {e}")
            return None


class LogParser:
    """Parser per estrazione dati strutturati dai log testuali."""
    
    # Pattern regex per estrazione dati dai log
    PATTERNS = {
        'regime': r'regime=(\w+)',
        'strategy': r'strategy=(\w+)',
        'tech_signal': r'🟢 SIGNAL: (BUY|SELL|HOLD|CLOSE)',
        'decision_type': r'DECISION (APPROVED|REJECTED)',
        'block_reason': r'BLOCK: .+ \((.+)\)',
        'intel_score': r'score=([-\d.]+)',
        'intel_bias': r'bias=(bullish|bearish|neutral)',
        'trend_direction': r'trend=(converging|diverging|stable)',
        'trade': r'TRADE:.*side=(BUY|SELL)',
    }
    
    def parse_lines_to_records(self, content: str) -> List[Dict[str, Any]]:
        """Estrae record strutturati da linee di log.
        
        Args:
            content: Contenuto del log testuale
        
        Returns:
            Lista di record strutturati
        """
        records = []
        lines = content.split('\n')
        
        for line in lines:
            if not line.strip():
                continue
            
            record = {'raw_line': line}
            
            # Estrai pattern noti
            for key, pattern in self.PATTERNS.items():
                match = re.search(pattern, line)
                if match:
                    record[key] = match.group(1)
            
            if len(record) > 1:  # almeno un pattern matchato
                records.append(record)
        
        return records
    
    def parse_to_structured_data(self, content: str) -> Dict[str, Any]:
        """Estrae dati aggregati dal log per analisi.
        
        Args:
            content: Contenuto del log testuale
        
        Returns:
            Dict con metriche aggregate (decisioni, segnali, trade, etc.)
        """
        records = self.parse_lines_to_records(content)
        
        analysis = {
            'total_lines': len(content.split('\n')),
            'structured_records': len(records),
            'decisions': {
                'total': 0,
                'approved': 0,
                'rejected': 0,
                'rejected_reasons': {}
            },
            'signals': {
                'total': 0,
                'buy': 0,
                'sell': 0,
                'hold': 0,
                'close': 0
            },
            'trades': {
                'total': 0,
                'buy': 0,
                'sell': 0
            },
            'regime_changes': {},
            'strategies_used': {},
            'intel_scores': [],
            'blocks': {
                'total': 0,
                'reasons': {}
            }
        }
        
        for record in records:
            # Decisioni
            if 'decision_type' in record:
                analysis['decisions']['total'] += 1
                if record['decision_type'] == 'APPROVED':
                    analysis['decisions']['approved'] += 1
                elif record['decision_type'] == 'REJECTED':
                    analysis['decisions']['rejected'] += 1
            
            # Segnali
            if 'tech_signal' in record:
                analysis['signals']['total'] += 1
                signal = record['tech_signal'].lower()
                if signal in analysis['signals']:
                    analysis['signals'][signal] += 1
            
            # Trade
            if 'trade' in record:
                analysis['trades']['total'] += 1
                side = record['trade'].lower()
                if side in analysis['trades']:
                    analysis['trades'][side] += 1
            
            # Regime
            if 'regime' in record:
                regime = record['regime']
                analysis['regime_changes'][regime] = analysis['regime_changes'].get(regime, 0) + 1
            
            # Strategy
            if 'strategy' in record:
                strategy = record['strategy']
                analysis['strategies_used'][strategy] = analysis['strategies_used'].get(strategy, 0) + 1
            
            # Intel score
            if 'intel_score' in record:
                try:
                    score = float(record['intel_score'])
                    analysis['intel_scores'].append(score)
                except ValueError:
                    pass
            
            # Blocks
            if 'block_reason' in record:
                analysis['blocks']['total'] += 1
                reason = record['block_reason']
                analysis['blocks']['reasons'][reason] = analysis['blocks']['reasons'].get(reason, 0) + 1
        
        return analysis
    
    def extract_pipeline_context(self, log_line: str) -> Optional[Dict[str, str]]:
        """Estrae contesto da una linea PIPELINE.
        
        Args:
            log_line: Linea di log PIPELINE
        
        Returns:
            Dict con regime, strategy e altri campi se trovati
        """
        if 'PIPELINE:' not in log_line:
            return None
        
        context = {}
        
        regime_match = re.search(r'regime=(\w+)', log_line)
        if regime_match:
            context['regime'] = regime_match.group(1)
        
        strategy_match = re.search(r'strategy=(\w+)', log_line)
        if strategy_match:
            context['strategy'] = strategy_match.group(1)
        
        vol_anomaly = 'vol_anomaly=True' in log_line
        context['vol_anomaly'] = vol_anomaly
        
        tradeable = 'tradeable=True' in log_line
        context['tradeable'] = tradeable
        
        return context if context else None