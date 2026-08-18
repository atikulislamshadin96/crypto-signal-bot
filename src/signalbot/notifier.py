from __future__ import annotations

import logging
import os
from typing import Iterable

import requests

LOGGER = logging.getLogger(__name__)


def send_telegram(message: str) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        LOGGER.info("Telegram is not configured; skipping notification.")
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        response = requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=20)
        response.raise_for_status()
        return True
    except requests.RequestException as exc:
        LOGGER.error("Telegram notification failed: %s", exc)
        return False


def send_discord(message: str) -> bool:
    webhook = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook:
        LOGGER.info("Discord is not configured; skipping notification.")
        return False
    try:
        response = requests.post(webhook, json={"content": message[:1900]}, timeout=20)
        response.raise_for_status()
        return True
    except requests.RequestException as exc:
        LOGGER.error("Discord notification failed: %s", exc)
        return False


def notify(message: str, config: dict) -> dict[str, bool]:
    notification_cfg = config.get("notifications", {})
    results: dict[str, bool] = {}
    if notification_cfg.get("telegram_enabled", True):
        results["telegram"] = send_telegram(message)
    if notification_cfg.get("discord_enabled", True):
        results["discord"] = send_discord(message)
    return results
