"""Entry point: fetch data, analyze, and dispatch alerts."""
from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone, timedelta

from . import alerts
from .config import get_secrets, load_config
from .data import fetch_history
from .signals import analyze

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("stock-monitor")

# IST is UTC+5:30
IST = timezone(timedelta(hours=5, minutes=30))


def run() -> int:
    config = load_config()
    secrets = get_secrets()

    watchlist = config.get("watchlist", [])
    if not watchlist:
        log.error("Watchlist is empty — nothing to monitor.")
        return 1

    log.info("Monitoring %d symbols", len(watchlist))
    history = fetch_history(
        watchlist,
        period=config.get("history_period", "1y"),
        interval=config.get("interval", "1d"),
    )

    if not history:
        log.error("No price data could be fetched for any symbol.")
        return 1

    all_signals = []
    for symbol, df in history.items():
        try:
            sig = analyze(symbol, df, config)
            all_signals.append(sig)
            log.info(
                "%s → %s (score %.2f, price ₹%.2f)",
                symbol, sig.action, sig.score, sig.price,
            )
        except Exception as exc:
            log.warning("Analysis failed for %s: %s", symbol, exc)

    # Filter to actionable signals based on config.
    notify_on = set(config.get("alerts", {}).get("notify_on", ["BUY", "SELL"]))
    actionable = [s for s in all_signals if s.action in notify_on]
    # Strongest convictions first.
    actionable.sort(key=lambda s: abs(s.score), reverse=True)

    as_of = datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")

    send_empty = config.get("alerts", {}).get("send_empty_digest", False)
    if not actionable and not send_empty:
        log.info("No actionable signals and send_empty_digest=false — no alerts sent.")
        _print_summary(all_signals)
        return 0

    status = alerts.dispatch(secrets, actionable, as_of)
    log.info("Alert dispatch status: %s", status)
    if not any(status.values()):
        log.warning(
            "No alert channel is configured. Set SMTP_* and/or TELEGRAM_* "
            "environment variables / GitHub secrets to receive alerts."
        )
    _print_summary(all_signals)
    return 0


def _print_summary(signals) -> None:
    """Emit a console summary (useful in the Actions log)."""
    print("\n===== Stock Monitor Summary =====")
    for s in sorted(signals, key=lambda x: abs(x.score), reverse=True):
        print(f"{s.action:5s}  {s.symbol:16s}  ₹{s.price:<10}  score={s.score}")
    print("=================================\n")


if __name__ == "__main__":
    sys.exit(run())
