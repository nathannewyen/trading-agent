"""Price threshold alerts with optional webhook notification.

Checks whether a ticker's current price has crossed a user-defined threshold
and records alert history to disk so the same alert isn't fired repeatedly.
"""

import json
import logging
import os
import time
import urllib.request
from pathlib import Path

import yfinance as yf

logger = logging.getLogger(__name__)

ALERTS_DIR = Path(os.getenv("ALERTS_DIR", ".alerts"))


def _alert_path(ticker: str, threshold: float, direction: str) -> Path:
    key = f"{ticker.upper()}_{direction}_{threshold:.4f}".replace(".", "p")
    return ALERTS_DIR / f"{key}.json"


def _load_history(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _save_history(path: Path, data: dict) -> None:
    ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def check_price_alert(
    ticker: str,
    threshold: float,
    direction: str = "above",
    webhook_url: str | None = None,
    cooldown_seconds: int = 3600,
) -> dict:
    """Check if *ticker*'s current price has crossed *threshold*.

    Args:
        ticker: Stock symbol.
        threshold: Price level to watch.
        direction: 'above' fires when price >= threshold; 'below' when price <= threshold.
        webhook_url: Optional URL to POST a JSON alert payload to.
        cooldown_seconds: Minimum seconds between repeated alerts for the same condition.

    Returns:
        dict with keys: ticker, current_price, threshold, direction, triggered, message.
    """
    if direction not in ("above", "below"):
        return {"error": f"direction must be 'above' or 'below', got {direction!r}"}

    try:
        info = yf.Ticker(ticker).fast_info
        current_price = float(info.last_price)
    except Exception as exc:
        logger.error(f"Failed to fetch price for {ticker}: {exc}")
        return {"error": str(exc), "ticker": ticker}

    triggered = (direction == "above" and current_price >= threshold) or (
        direction == "below" and current_price <= threshold
    )

    history_path = _alert_path(ticker, threshold, direction)
    history = _load_history(history_path)
    last_fired = history.get("last_fired", 0)
    now = time.time()

    message = (
        f"{ticker.upper()} at ${current_price:.2f} has crossed {direction} ${threshold:.2f}"
        if triggered
        else f"{ticker.upper()} at ${current_price:.2f} — threshold ${threshold:.2f} ({direction}) not yet reached"
    )

    if triggered and (now - last_fired) >= cooldown_seconds:
        history["last_fired"] = now
        history["price_at_trigger"] = current_price
        _save_history(history_path, history)

        if webhook_url:
            _send_webhook(webhook_url, {"ticker": ticker.upper(), "price": current_price,
                                         "threshold": threshold, "direction": direction, "message": message})

    return {
        "ticker": ticker.upper(),
        "current_price": current_price,
        "threshold": threshold,
        "direction": direction,
        "triggered": triggered,
        "message": message,
    }


def _send_webhook(url: str, payload: dict) -> None:
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            logger.info(f"Webhook delivered: {resp.status}")
    except Exception as exc:
        logger.warning(f"Webhook delivery failed: {exc}")


def send_slack_alert(webhook_url: str, ticker: str, message: str) -> bool:
    """Send a formatted Slack message via an incoming webhook URL.

    Args:
        webhook_url: Slack Incoming Webhook URL (from Slack app settings).
        ticker: Stock ticker for the alert subject.
        message: Human-readable alert text.

    Returns:
        True if delivered successfully, False otherwise.
    """
    payload = {
        "text": f":bell: *Trading Alert: {ticker.upper()}*\n{message}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":bell: *Trading Alert: {ticker.upper()}*\n{message}",
                },
            }
        ],
    }
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url, data=data,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            logger.info(f"Slack alert delivered: {resp.status}")
            return True
    except Exception as exc:
        logger.warning(f"Slack alert failed: {exc}")
        return False


def list_alert_history() -> list[dict]:
    """Return all recorded alert fire events from disk."""
    if not ALERTS_DIR.exists():
        return []
    records = []
    for f in sorted(ALERTS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            data["_file"] = f.name
            records.append(data)
        except json.JSONDecodeError:
            pass
    return records
