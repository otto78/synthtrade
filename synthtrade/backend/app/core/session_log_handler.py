"""SessionLogHandler — accumula tutti i log (DEBUG+) di una sessione in memoria.

Feature:
- Accumulo in-memory con truncation automatico (max 50K entries)
- Persistenza live su DB (periodic save ogni N secondi)
- Salvataggio finale su DB allo stop della sessione
- Analisi strutturata dei log all'output

Uso:
    from app.core.session_log_handler import SessionLogHandler
    handler = SessionLogHandler()
    handler.attach()                                         # attach on session start
    handler.detach()                                         # detach on session stop
    content = handler.get_formatted_content(session_id, symbol)  # get text dump
"""
import logging
import os
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Callable


# I logger che hanno propagate=False in setup_logging() — vanno agganciati direttamente
_FORCED_LOGGER_NAMES = [
    "app.scalping.router",
    "app.scalping.engine.execution_loop",
    "app.scalping.engine.signal_aggregator",
    "app.scalping.engine.ws_client",
    "app.scalping.intelligence.signal_score_engine",
]


# Costanti di configurazione
_MAX_BUFFER_ENTRIES = 50_000  # Soluzione 2: max righe nel buffer prima del truncation
_TRUNCATE_KEEP_RATIO = 0.5    # Quando si tronca, tiene il 50% più recente (25K)


class SessionLogHandler(logging.Handler):
    """Handler di logging in-memory che accumula i record di una sessione.

    Al flush, arricchisce il dump con sezioni strutturate per l'analisi.

    Soluzione 1 — Persistenza live su DB:
        Imposta `set_persist_callback()` con una funzione che salva il contenuto
        formattato su DB. Il callback viene chiamato periodicamente da un task
        asincrono esterno (gestito da router.py).

    Soluzione 2 — Buffer truncation:
        Se il buffer supera _MAX_BUFFER_ENTRIES (50K), vengono rimosse le entry
        più vecchie mantenendo solo il _TRUNCATE_KEEP_RATIO (50%) più recente.
        Un marker [--- TRUNCATED X entries ---] viene inserito per tracciare
        la perdita di dati.
    """

    def __init__(self, level: int = logging.DEBUG, session_id: str = "", db_session_id: str = ""):
        super().__init__(level=level)
        self._buffer: list[str] = []
        self._raw_records: list[logging.LogRecord] = []
        # Soluzione 1: callback per persistenza live su DB
        self._persist_callback: Optional[Callable[[str], None]] = None
        # Contatore truncation per marker nei log
        self._truncated_count: int = 0
        # Identificatori sessione per il callback di persistenza
        self.session_id: str = session_id
        self.db_session_id: str = db_session_id
        self.symbol: str = "UNKNOWN"
        # Timestamp ultimo persist riuscito
        self._last_persist_at: Optional[datetime] = None

    # ------------------------------------------------------------------
    # Soluzione 1: Persistenza live su DB
    # ------------------------------------------------------------------
    def set_persist_callback(self, callback: Optional[Callable[[str], None]]) -> None:
        """Imposta il callback per la persistenza live su DB.
        
        Il callback riceve il contenuto formattato del log come stringa.
        Può essere una funzione sincrona (eseguita in un thread) o un wrapper
        che pianifica un task asincrono.
        """
        self._persist_callback = callback

    def persist_now(self, force: bool = False) -> bool:
        """Salva i log accumulati su DB ora (se callback configurato).
        
        Args:
            force: Se True, salva anche se il buffer è vuoto (utile allo stop).
                   Se False, salva solo se il buffer contiene dati.
        
        Returns:
            True se il callback è stato chiamato, False altrimenti.
        """
        if not self._persist_callback:
            return False
        if not force and not self._buffer:
            return False
        
        content = self.get_formatted_content(self.session_id, self.symbol)
        if not content:
            return False
        
        try:
            self._persist_callback(content)
            self._last_persist_at = datetime.now(timezone.utc)
            return True
        except Exception:
            return False

    @property
    def last_persist_at(self) -> Optional[datetime]:
        return self._last_persist_at

    def _maybe_truncate(self) -> None:
        """Soluzione 2: tronca il buffer se supera _MAX_BUFFER_ENTRIES.
        
        Rimuove le entry più vecchie mantenendo _TRUNCATE_KEEP_RATIO (50%)
        del buffer più recente. Inserisce un marker per tracciare la perdita.
        """
        if len(self._buffer) <= _MAX_BUFFER_ENTRIES:
            return
        
        keep_count = int(_MAX_BUFFER_ENTRIES * _TRUNCATE_KEEP_RATIO)
        removed_count = len(self._buffer) - keep_count
        
        # Tieni solo la parte più recente
        self._buffer = self._buffer[-keep_count:]
        self._raw_records = self._raw_records[-keep_count:]
        
        self._truncated_count += removed_count
        
        # Inserisci marker di truncation
        marker = f"[--- TRUNCATED {removed_count} old entries (total truncated: {self._truncated_count}) ---]"
        self._buffer.insert(0, marker)

    def emit(self, record: logging.LogRecord) -> None:
        """Accumula il record formattato nel buffer con timestamp.

        Formatta manualmente senza dipendere da filtri esterni:
        - Usa il format del record stesso (già formattato dall'handler principale)
        - Aggiunge solo timestamp + session_id se presente
        - NON usa self.format() per evitare dipendenza da SessionContextFilter
        
        Applica truncation automatico se il buffer supera 50K entries.
        """
        try:
            # Costruisci il timestamp dal record
            timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')

            # Usa il messaggio già formattato se possibile (record.getMessage() = msg raw)
            # Ricostruisce il formato come: [timestamp] asctime [levelname] session_id name: msg
            asctime = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S,%f')[:23]
            levelname = record.levelname
            session_id = getattr(record, 'session_id', '')
            name = record.name
            msg = record.getMessage()

            line = f"[{timestamp}] {asctime} [{levelname}]{session_id} {name}: {msg}"

            self._buffer.append(line)
            self._raw_records.append(record)
            
            # Soluzione 2: truncation automatico se il buffer cresce troppo
            self._maybe_truncate()
        except Exception:
            self.handleError(record)

    # ------------------------------------------------------------------
    # Attach / Detach — risolve il problema dei forced logger
    # ------------------------------------------------------------------
    def attach(self) -> None:
        """Attacca questo handler al root logger E a tutti i forced logger."""
        logging.getLogger().addHandler(self)
        for name in _FORCED_LOGGER_NAMES:
            logging.getLogger(name).addHandler(self)

    def detach(self) -> None:
        """Rimuove questo handler dal root logger E da tutti i forced logger."""
        logging.getLogger().removeHandler(self)
        for name in _FORCED_LOGGER_NAMES:
            logging.getLogger(name).removeHandler(self)

    # ------------------------------------------------------------------
    # Accesso ai dati
    # ------------------------------------------------------------------
    @property
    def log_count(self) -> int:
        return len(self._buffer)

    def get_all(self) -> list[str]:
        """Restituisce una copia di tutti i log accumulati."""
        return list(self._buffer)

    # ------------------------------------------------------------------
    # Analisi strutturata dei log
    # ------------------------------------------------------------------
    def _analyze(self) -> Dict[str, Any]:
        """Analizza i log accumulati e restituisce metriche strutturate."""
        analysis: Dict[str, Any] = {
            "decisions": {
                "total": 0,
                "approved": 0,
                "rejected": 0,
                "rejected_reasons": Counter(),
            },
            "signals": {
                "total": 0,
                "buy": 0,
                "sell": 0,
                "blocked": 0,
                "blocked_reasons": Counter(),
            },
            "trades": {
                "total": 0,
                "buy": 0,
                "sell": 0,
                "ocl_filled": 0,
                "ocl_expired": 0,
                "pipeline_decisions": [],
            },
            "regime_changes": Counter(),
            "strategies_used": Counter(),
            "intel_scores": [],
            "vol_anomalies": 0,
            "hold_signals": Counter(),
            "threshold_changes": [],
            "supervisor_decisions": [],
            "warnings": [],
            "errors": [],
        }

        for record in self._raw_records:
            msg = record.getMessage()
            name = record.name
            level = record.levelno

            # Livelli
            if level >= logging.ERROR:
                analysis["errors"].append(msg)
            elif level >= logging.WARNING:
                analysis["warnings"].append(msg)

            # Pipeline decisions
            if "PIPELINE:" in msg:
                analysis["decisions"]["total"] += 1
                analysis["trades"]["pipeline_decisions"].append(msg)
                regime_match = re.search(r'regime=(\w+)', msg)
                if regime_match:
                    analysis["regime_changes"][regime_match.group(1)] += 1
                strategy_match = re.search(r'strategy=(\w+)', msg)
                if strategy_match:
                    analysis["strategies_used"][strategy_match.group(1)] += 1
                if "vol_anomaly=True" in msg:
                    analysis["vol_anomalies"] += 1

            # Decisioni APPROVED/REJECTED
            if "DECISION APPROVED" in msg:
                analysis["decisions"]["approved"] += 1
            elif "DECISION REJECTED" in msg:
                analysis["decisions"]["rejected"] += 1
                reason_match = re.search(r'DECISION REJECTED: (.+)', msg)
                if reason_match:
                    analysis["decisions"]["rejected_reasons"][reason_match.group(1)] += 1

            # Segnali BUY/SELL/BLOCK
            if "SIGNAL:" in msg:
                analysis["signals"]["total"] += 1
                if "SIGNAL: BUY" in msg:
                    analysis["signals"]["buy"] += 1
                elif "SIGNAL: SELL" in msg:
                    analysis["signals"]["sell"] += 1
            if "BLOCK:" in msg:
                analysis["signals"]["blocked"] += 1
                block_match = re.search(r'BLOCK: .+ \((.+)\)', msg)
                if block_match:
                    analysis["signals"]["blocked_reasons"][block_match.group(1)] += 1

            # TRADE execution
            if ">>> TRADE:" in msg:
                analysis["trades"]["total"] += 1
                if "side=BUY" in msg:
                    analysis["trades"]["buy"] += 1
                elif "side=SELL" in msg:
                    analysis["trades"]["sell"] += 1

            # OCO events
            if "OCO FILLED" in msg:
                analysis["trades"]["ocl_filled"] += 1
            if "OCO EXPIRED" in msg:
                analysis["trades"]["ocl_expired"] += 1

            # Intel scores (con protezione per valori non numerici come "score=N/A")
            if "score=" in msg and "bias=" in msg and "Intel snapshot" in msg:
                score_match = re.search(r'score=([-\d.]+)', msg)
                if score_match:
                    try:
                        score_val = float(score_match.group(1))
                        analysis["intel_scores"].append(score_val)
                    except ValueError:
                        pass  # Ignora score non numerici (es. "N/A")

            # HOLD signals
            if ">>> HOLD:" in msg:
                hold_match = re.search(r'HOLD: existing (\w+) position', msg)
                if hold_match:
                    analysis["hold_signals"][hold_match.group(1)] += 1

            # Threshold changes
            if "Auto-decay:" in msg:
                threshold_match = re.search(r'Soglia ([\d.]+).*?([\d.]+)', msg)
                if threshold_match:
                    analysis["threshold_changes"].append({
                        "from": float(threshold_match.group(1)),
                        "to": float(threshold_match.group(2)),
                    })

            # Supervisor decisions
            if "Supervisor decision broadcasted:" in msg:
                action_match = re.search(r'action=(\w+)', msg)
                if action_match:
                    analysis["supervisor_decisions"].append(action_match.group(1))

        return analysis

    def _format_analysis_section(self, analysis: Dict[str, Any]) -> str:
        """Formatta l'analisi come sezione leggibile."""
        lines = []
        lines.append(f"\n{'=' * 72}")
        lines.append(" SESSION ANALYSIS SUMMARY")
        lines.append(f"{'=' * 72}\n")

        # Decisioni
        d = analysis["decisions"]
        lines.append(f"Decisioni: {d['total']} totali | {d['approved']} approvate | {d['rejected']} rifiutate")
        if d["rejected_reasons"]:
            lines.append("   Top motivi rifiuto:")
            for reason, count in d["rejected_reasons"].most_common(5):
                lines.append(f"     - {reason} (x{count})")

        # Segnali
        s = analysis["signals"]
        lines.append(f"Segnali: {s['total']} totali | BUY={s['buy']} SELL={s['sell']} | bloccati={s['blocked']}")
        if s["blocked_reasons"]:
            lines.append("   Top motivi blocco:")
            for reason, count in s["blocked_reasons"].most_common(5):
                lines.append(f"     - {reason} (x{count})")

        # Trade
        t = analysis["trades"]
        lines.append(f"Trades: {t['total']} eseguiti | BUY={t['buy']} SELL={t['sell']}")
        lines.append(f"   OCO: {t['ocl_filled']} filled, {t['ocl_expired']} expired")

        # Intel score range
        if analysis["intel_scores"]:
            scores = analysis["intel_scores"]
            lines.append(f"Intelligence: min={min(scores):.1f} max={max(scores):.1f} avg={sum(scores)/len(scores):.1f}")

        # Regime
        if analysis["regime_changes"]:
            lines.append(f"Regime: {dict(analysis['regime_changes'])}")

        # Strategies
        if analysis["strategies_used"]:
            lines.append(f"Strategie: {dict(analysis['strategies_used'])}")

        # Hold signals
        if analysis["hold_signals"]:
            lines.append(f"HOLD: {dict(analysis['hold_signals'])}")

        # Vol anomalies
        if analysis["vol_anomalies"]:
            lines.append(f"Anomalie volume: {analysis['vol_anomalies']}")

        # Threshold changes
        if analysis["threshold_changes"]:
            lines.append(f"Soglia cambiata: {analysis['threshold_changes']}")

        # Supervisor decisions
        if analysis["supervisor_decisions"]:
            from collections import Counter as C
            sup_counts = C(analysis["supervisor_decisions"])
            lines.append(f"Supervisor: {dict(sup_counts)}")

        # Warning/Error count
        if analysis["errors"]:
            lines.append(f"ERRORI: {len(analysis['errors'])}")
        if analysis["warnings"]:
            lines.append(f"WARNINGS: {len(analysis['warnings'])}")

        lines.append(f"{'=' * 72}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Output formattato
    # ------------------------------------------------------------------
    def get_formatted_content(
        self,
        session_id: str = "",
        symbol: str = "",
    ) -> Optional[str]:
        """Restituisce il contenuto formattato dei log come stringa (senza scrivere su file).

        Include una sezione di analisi strutturata alla fine del dump.
        Se session_id o symbol non forniti, usa quelli interni dell'handler.

        Args:
            session_id: ID della sessione (usa self.session_id se omesso)
            symbol: Simbolo trading (usa self.symbol se omesso)

        Returns:
            Contenuto formattato del log, oppure None se buffer vuoto.
        """
        if not self._buffer:
            return None

        sid = session_id or self.session_id
        sym = symbol or self.symbol
        safe_symbol = sym.replace("/", "_").upper()
        header = (
            f"{'=' * 72}\n"
            f" SESSION LOG DUMP\n"
            f" Session ID : {sid}\n"
            f" Symbol     : {safe_symbol}\n"
            f" Entries    : {len(self._buffer)}\n"
            f" Generated  : {datetime.now(timezone.utc).isoformat()}\n"
            f"{'=' * 72}\n\n"
        )

        # Build analysis section FIRST so it appears at the top
        analysis_section_str = ""
        try:
            analysis = self._analyze()
            analysis_section_str = self._format_analysis_section(analysis)
        except Exception as exc:
            analysis_section_str = (
                f"\n{'=' * 72}\n"
                f" SESSION ANALYSIS NOT AVAILABLE: {exc}\n"
                f"{'=' * 72}\n"
            )

        # Place analysis right after header, then all log entries
        lines = [header, analysis_section_str + "\n"]
        for line in self._buffer:
            lines.append(line + "\n")

        return "".join(lines)

    def get_structured_analysis(self) -> Dict[str, Any]:
        """Restituisce l'analisi strutturata come dict JSON-serializable.

        Utile per l'endpoint API che serve il dump in formato JSON.
        """
        return self._analyze()

    def get_content(self, session_id: str = "", symbol: str = "") -> Optional[str]:
        """Alias per get_formatted_content.

        Deprecato: mantenuto per backward compatibilità, preferire get_formatted_content.
        """
        return self.get_formatted_content(session_id, symbol)

    def flush_to_file(
        self,
        session_id: str = "",
        symbol: str = "",
        log_dir: str = "session_logs",
    ) -> Optional[str]:
        """Scrive i log accumulati su un file .txt.

        Args:
            session_id: ID della sessione (usa self.session_id se omesso)
            symbol: Simbolo trading (usa self.symbol se omesso)
            log_dir: Directory di output (default: session_logs/)

        Returns:
            Percorso assoluto del file creato, oppure None se buffer vuoto.
        """
        if not self._buffer:
            return None

        sid = session_id or self.session_id
        sym = symbol or self.symbol

        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_symbol = sym.replace("/", "_").upper()
        filename = f"session_{safe_symbol}_{sid}_{timestamp}.txt"
        filepath = os.path.abspath(os.path.join(log_dir, filename))

        content = self.get_formatted_content(sid, sym)
        if content is None:
            return None

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        self._buffer.clear()
        self._raw_records.clear()
        return filepath