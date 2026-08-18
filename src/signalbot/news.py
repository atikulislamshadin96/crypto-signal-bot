from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlparse

import requests
import xml.etree.ElementTree as ET

from .models import NewsItem

LOGGER = logging.getLogger(__name__)


def _parse_date(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        parsed = parsedate_to_datetime(value)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            return datetime.now(timezone.utc)


def classify_text(title: str, positive: list[str], negative: list[str], high_impact: list[str]) -> tuple[str, str, list[str]]:
    text = title.lower()
    pos = [word for word in positive if re.search(rf"\b{re.escape(word.lower())}\b", text)]
    neg = [word for word in negative if re.search(rf"\b{re.escape(word.lower())}\b", text)]
    impact = [word for word in high_impact if re.search(rf"\b{re.escape(word.lower())}\b", text)]
    if len(pos) > len(neg):
        sentiment = "Positive"
    elif len(neg) > len(pos):
        sentiment = "Negative"
    else:
        sentiment = "Neutral"
    return sentiment, ("high" if impact else "normal"), sorted(set(pos + neg + impact))


def fetch_news(config: dict[str, Any]) -> list[NewsItem]:
    news_cfg = config.get("news", {})
    if not news_cfg.get("enabled", True):
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=float(news_cfg.get("lookback_hours", 4)))
    items: list[NewsItem] = []
    for feed_url in news_cfg.get("rss_urls", []):
        try:
            response = requests.get(feed_url, timeout=15, headers={"User-Agent": "crypto-signal-bot/1.0"})
            response.raise_for_status()
            root = ET.fromstring(response.content)
            for entry in root.findall(".//item"):
                title = (entry.findtext("title") or "").strip()
                if not title:
                    continue
                published = _parse_date(entry.findtext("pubDate") or entry.findtext("published"))
                if published < cutoff:
                    continue
                url = (entry.findtext("link") or "").strip()
                sentiment, impact, matched = classify_text(
                    title,
                    list(news_cfg.get("positive_keywords", [])),
                    list(news_cfg.get("negative_keywords", [])),
                    list(news_cfg.get("high_impact_keywords", [])),
                )
                items.append(NewsItem(title, url, published.isoformat(), urlparse(feed_url).netloc, sentiment, impact, matched))
        except (requests.RequestException, ET.ParseError, OSError) as exc:
            LOGGER.warning("News feed failed (%s): %s", feed_url, exc)
    items.sort(key=lambda item: item.published_at, reverse=True)
    return items[: int(news_cfg.get("max_items", 40))]


def news_filter(symbol: str, side: str, items: list[NewsItem], config: dict[str, Any]) -> tuple[bool, list[str], str]:
    """Return (blocked, context, aggregate sentiment). High-impact volatility is conservative."""
    symbol_root = symbol.split("/")[0].lower()
    relevant = [item for item in items if symbol_root in item.title.lower() or symbol_root in item.url.lower() or symbol_root == "btc" and "bitcoin" in item.title.lower() or symbol_root == "eth" and "ethereum" in item.title.lower()]
    high_impact = [item for item in items if item.impact == "high"]
    negative = sum(item.sentiment == "Negative" for item in relevant)
    positive = sum(item.sentiment == "Positive" for item in relevant)
    aggregate = "Negative" if negative > positive else "Positive" if positive > negative else "Neutral"
    context = [item.title for item in (relevant + high_impact)[:3]]
    blocked = bool(high_impact) or (side == "LONG" and aggregate == "Negative") or (side == "SHORT" and aggregate == "Positive")
    return blocked, context, aggregate
