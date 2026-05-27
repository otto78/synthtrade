"""Opportunity Monitor (TASK-810).

Rilevamento automatico di opportunità di mercato.
"""

from app.scalping.opportunity.pollers.base import BasePoller
from app.scalping.opportunity.pollers.binance_rss import BinanceRSSPoller
from app.scalping.opportunity.pollers.coingecko import CoinGeckoPoller
from app.scalping.opportunity.pollers.whale_alert import WhaleAlertPoller
from app.scalping.opportunity.pollers.news import NewsPoller
from app.scalping.opportunity.deduplicator import Deduplicator
from app.scalping.opportunity.classifier import OpportunityClassifier
from app.scalping.opportunity.router import OpportunityRouter
from app.scalping.opportunity.scheduler import OpportunityScheduler

__all__ = [
    "BasePoller",
    "BinanceRSSPoller",
    "CoinGeckoPoller",
    "WhaleAlertPoller",
    "NewsPoller",
    "Deduplicator",
    "OpportunityClassifier",
    "OpportunityRouter",
    "OpportunityScheduler",
]