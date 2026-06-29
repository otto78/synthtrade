"""SessionLogHandttura tutti i log (DEBUG+) di una sessione in memoriae li scrive su file .txt quando la sessione termina.

Problema root-cause risol forced logger in setup_logging() hanno propagate=False, quindi i loro messaggiNON arrivano al root logger dove SessionLogHandler è attaccato.
Soluzione: attach() aggancia l'handler direttamente aitiliz
    from app.core.session_log_handler import SessionLogHandler
    handler = SessionLogHandler()
    handler.attach()                                         # attach on session start
    handler.detach()                                         # detach on session stop
    content = handler.get_formatted_content(session_id, symbol)  # get text dump
    filepath = handler.flush_to_file(session_id, symbol)     # write to file
"""
import logging
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any


# I logger che hanno propagate=False in setup_logging() — vanno agganciati direttamente
_FORCED_LOGGER_NAMES = [
    "app.scalping.router",
    "app.scalping.engine.execution_loop",
    "app.scalping.engine.signal_aggregator",
    "app.scalping.engine.ws_client",
    "app.scalping.intelligence.signal_score_engine",
]


class SessionLogHandler(logging.Handler):
    """Handler di logging in-memory che accumula i record di una sessione.

    Al flush, arricchisce il dump con sezioni strutturate per l'analisi.
    """

    def __init__(self, level: int = logging.DEBUG):
        super().__init__(level=level)
        self._buffer: list[str] = []
        self._raw_records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        """Accumula il record formattato nel buffer con timestamp.

        Formatta manualmente senza dipendere da filtri esterni:
        - Usa il format del record stesso (già formattato dall'handler principale)
        - Aggiunge solo timestamp + session_id se presente
        - NON usa self.format() per evitare dipendenza da SessionContextFilter
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
        session_id: str,
        symbol: str = "UNKNOWN",
    ) -> Optional[str]:
        """Restituisce il contenuto formattato dei log come stringa (senza scrivere su file).

        Include una sezione di analisi strutturata alla fine del dump.

        Args:
            session_id: ID della sessione
            symbol: Simbolo trading per arricchire l'header

        Returns:
            Contenuto formattato del log, oppure None se buffer vuoto.
        """
        if not self._buffer:
            return None

        safe_symbol = symbol.replace("/", "_").upper()
        header = (
            f"{'=' * 72}\n"
            f" SESSION LOG DUMP\n"
            f" Session ID : {session_id}\n"
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

    def get_content(self, session_id: str, symbol: str = "UNKNOWN") -> Optional[str]:
        """Alias per get_formatted_content.

        Deprecato: mantenuto per backward compatibilità, preferire get_formatted_content.
        """
        return self.get_formatted_content(session_id, symbol)

    def flush_to_file(
        self,
        session_id: str,
        symbol: str = "UNKNOWN",
        log_dir: str = "session_logs",
    ) -> Optional[str]:
        """Scrive i log accumulati su un file .txt.

        Args:
            session_id: ID della sessione (es. "sess_a1b2c3d4")
            symbol: Simbolo trading per arricchire il filename
            log_dir: Directory di output (default: session_logs/)

        Returns:
            Percorso assoluto del file creato, oppure None se buffer vuoto.
        """
        if not self._buffer:
            return None

        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_symbol = symbol.replace("/", "_").upper()
        filename = f"session_{safe_symbol}_{session_id}_{timestamp}.txt"
        filepath = os.path.abspath(os.path.join(log_dir, filename))

        content = self.get_formatted_content(session_id, symbol)
        if content is None:
            return None

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        self._buffer.clear()
        self._raw_records.clear()
        return filepath