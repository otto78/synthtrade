"""Test standalone per SessionLogHandler - non dipende dal progetto."""
import sys
import logging
import os
import re
from collections import Counter
from datetime import datetime, timezone

# Inline della classe SessionLogHandler per test isolato
_FORCED_LOGGER_NAMES = [
    "app.scalping.router",
    "app.scalping.engine.execution_loop",
    "app.scalping.engine.signal_aggregator",
    "app.scalping.engine.ws_client",
    "app.scalping.intelligence.signal_score_engine",
]

class SessionLogHandler(logging.Handler):
    def __init__(self, level=logging.DEBUG):
        super().__init__(level=level)
        self._buffer = []
        self._raw_records = []

    def emit(self, record):
        try:
            timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
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

    def attach(self):
        logging.getLogger().addHandler(self)
        for name in _FORCED_LOGGER_NAMES:
            logging.getLogger(name).addHandler(self)

    def detach(self):
        logging.getLogger().removeHandler(self)
        for name in _FORCED_LOGGER_NAMES:
            logging.getLogger(name).removeHandler(self)

    @property
    def log_count(self):
        return len(self._buffer)

    def _analyze(self):
        analysis = {"decisions": {"total": 0, "approved": 0, "rejected": 0, "rejected_reasons": Counter()}}
        for record in self._raw_records:
            msg = record.getMessage()
            if "PIPELINE:" in msg:
                analysis["decisions"]["total"] += 1
            if "DECISION APPROVED" in msg:
                analysis["decisions"]["approved"] += 1
            elif "DECISION REJECTED" in msg:
                analysis["decisions"]["rejected"] += 1
                m = re.search(r'DECISION REJECTED: (.+)', msg)
                if m:
                    analysis["decisions"]["rejected_reasons"][m.group(1)] += 1
        return analysis

    def _format_analysis_section(self, analysis):
        lines = [f"\n{'=' * 72}", " SESSION ANALYSIS SUMMARY", f"{'=' * 72}\n"]
        d = analysis["decisions"]
        lines.append(f"📊 DECISIONI: {d['total']} totali | ✅ {d['approved']} approvate | ❌ {d['rejected']} rifiutate")
        if d["rejected_reasons"]:
            lines.append("   Top motivi rifiuto:")
            for reason, count in d["rejected_reasons"].most_common(5):
                lines.append(f"     - {reason} (x{count})")
        lines.append(f"\n{'=' * 72}")
        return "\n".join(lines)

    def get_formatted_content(self, session_id, symbol="UNKNOWN"):
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
        try:
            analysis = self._analyze()
            lines.append(self._format_analysis_section(analysis) + "\n")
        except Exception as e:
            lines.append(f"\n⚠️ ANALYSIS ERROR: {e}\n")
        return "".join(lines)


# ── TEST ──
print("=" * 60)
print("TEST: SessionLogHandler standalone")
print("=" * 60)

# Setup logging di base
logging.basicConfig(level=logging.INFO, force=True)

handler = SessionLogHandler()
handler.attach()

# Log come farebbe il sistema reale
logging.getLogger('app.scalping.router').info("Session started: sess_test")
logging.getLogger('app.scalping.engine.execution_loop').info("PIPELINE: bnbusdc regime=trending_down strategy=ema_cross tech=SELL@0.75")
logging.getLogger('app.scalping.engine.execution_loop').info(">>> HOLD: existing BUY position matches SELL signal")
logging.getLogger('app.scalping.engine.execution_loop').info("DECISION APPROVED -> test | confidence=0.55")
logging.getLogger('app.scalping.engine.execution_loop').info("DECISION REJECTED: |score|=8.9 < threshold 10.0")
logging.getLogger('app.scalping.engine.execution_loop').info("DECISION REJECTED: |score|=8.9 < threshold 10.0")
logging.getLogger('app.scalping.engine.execution_loop').info("DECISION REJECTED: posizione aperta: nessun nuovo ingresso")
logging.getLogger('app.scalping.engine.signal_aggregator').info("SIGNAL: BUY bnbusdc conf=0.415")
logging.getLogger('app.scalping.router').info(">>> TRADE: side=BUY has_open=False")

handler.detach()

print(f"\nBuffer entries: {handler.log_count}")
print(f"Raw records: {len(handler._raw_records)}")

content = handler.get_formatted_content("sess_test", "BNBUSDC")
if content:
    print(f"\nContent length: {len(content)} chars")
    print(f"HAS ANALYSIS: {'SESSION ANALYSIS SUMMARY' in content}")
    print("\n--- LAST 300 CHARS ---")
    print(content[-300:])
else:
    print("\nNO CONTENT GENERATED!")
    print(f"Buffer empty: {len(handler._buffer) == 0}")
    if handler._buffer:
        print(f"First entry: {handler._buffer[0][:80]}")

print("\n✅ TEST COMPLETE")