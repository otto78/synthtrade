"""
ModeFilterMixin — Aggiunge filtro automatico per modalità TEST/LIVE.

TASK-431: Tutti i repository che estendono questo mixin aggiungono
automaticamente `.eq("mode", current_mode)` a ogni query SELECT.

In questo modo, quando l'app è in modalità TEST, vede solo i dati TEST;
quando è in modalità LIVE, vede solo i dati LIVE.
I dati sono fisicamente separati ma vivono nelle stesse tabelle.
"""

from app.config import settings


class ModeFilterMixin:
    """Mixin per filtrare automaticamente per modalità (test/live).

    Alias: tutte le classi che estendono ModeFilterMixin e chiamano
    self._apply_mode_filter(query) prima di eseguire la query ricevono
    automaticamente il filtro.
    """

    def _apply_mode_filter(self, query):
        """Aggiunge il filtro mode alla query Supabase.

        Args:
            query: Oggetto query Supabase (es. self.db.table(...).select(...))

        Returns:
            Query con filtro .eq("mode", current_mode) aggiunto.
        """
        return query.eq("mode", settings.TRADING_MODE)

    def _filter_for_write(self, data: dict) -> dict:
        """Aggiunge automaticamente il campo mode ai dati in scrittura.

        Args:
            data: Dict da inserire/aggiornare

        Returns:
            Dict con campo mode aggiunto se non presente.
        """
        if "mode" not in data:
            data["mode"] = settings.TRADING_MODE
        return data