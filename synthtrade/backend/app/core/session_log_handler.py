"""SessionLogHandler — cattura tutti i log (DEBUG+) di una sessione in memoria
e li scrive su file .txt quando la sessione termina.

Utilizzo:
    from app.core.session_log_handler import SessionLogHandler
    handler = SessionLogHandler()
    logging.getLogger().addHandler(handler)       # attach on session start
    logging.getLogger().removeHandler(handler)    # detach on session stop
    filepath = handler.flush_to_file(session_id, symbol)
"""
import logging
import os
from datetime import datetime, timezone
from typing import Optional


class SessionLogHandler(logging.Handler):
    """Handler di logging in-memory che accumula i record di una sessione.

    Al flush, scrive tutto in un file testuale in session_logs/.
    Il formato include il session_id (grazie a SessionContextFilter).
    """

    def __init__(self, level: int = logging.DEBUG):
        super().__init__(level=level)
        self._buffer: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        """Accumula il record formattato nel buffer con timestamp."""
        try:
            msg = self.format(record)
            timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
            self._buffer.append(f"[{timestamp}] {msg}")
        except Exception:
            self.handleError(record)

    @property
    def log_count(self) -> int:
        return len(self._buffer)

    def get_all(self) -> list[str]:
        """Restituisce una copia di tutti i log accumulati."""
        return list(self._buffer)

    def get_formatted_content(
        self,
        session_id: str,
        symbol: str = "UNKNOWN",
    ) -> Optional[str]:
        """Restituisce il contenuto formattato dei log come stringa (senza scrivere su file).

        Utile per salvare il contenuto direttamente nel DB invece che su filesystem.

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

        lines = [header]
        for line in self._buffer:
            lines.append(line + "\n")

        return "".join(lines)

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

        header = (
            f"{'=' * 72}\n"
            f" SESSION LOG DUMP\n"
            f" Session ID : {session_id}\n"
            f" Symbol     : {safe_symbol}\n"
            f" Entries    : {len(self._buffer)}\n"
            f" Generated  : {datetime.now(timezone.utc).isoformat()}\n"
            f"{'=' * 72}\n\n"
        )

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(header)
            for line in self._buffer:
                f.write(line + "\n")

        self._buffer.clear()
        return filepath