"""Pollers for Opportunity Monitor."""

from app.scalping.opportunity.pollers.base import BasePoller
from app.scalping.opportunity.pollers.binance_rss import BinanceRSSPoller
from app.scalping.opportunity.pollers.coingecko import CoinGeckoPoller
from app.scalping.opportunity.pollers.whale_alert import WhaleAlertPoller
from app.scalping.opportunity.pollers.news import NewsPoller

__all__ = [
    "BasePoller",
    "BinanceRSSPoller",
    "CoinGeckoPoller",
    "WhaleAlertPoller",
    "NewsPoller",
]