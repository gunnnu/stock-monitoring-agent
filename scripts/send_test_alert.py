#!/usr/bin/env python3
"""Helper: send a test alert through whatever channels are configured.

This verifies your Email / Telegram credentials end-to-end WITHOUT waiting
for a real trading signal.

Usage (set the env vars you configured, then run):
  python scripts/send_test_alert.py

It uses the same code path as the live agent, so if this works the scheduled
runs will too.
"""
import os
import sys
from datetime import datetime, timezone, timedelta

# Allow running from the repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.alerts import dispatch          # noqa: E402
from src.config import get_secrets        # noqa: E402
from src.signals import Signal            # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))


def main() -> int:
    secrets = get_secrets()
    configured = []
    if secrets.get("smtp_host") and secrets.get("smtp_user") and secrets.get("email_to"):
        configured.append("email")
    if secrets.get("telegram_bot_token") and secrets.get("telegram_chat_id"):
        configured.append("telegram")

    if not configured:
        print("No channels configured. Set SMTP_* and/or TELEGRAM_* env vars first.")
        print("See .env.example for the full list.")
        return 1

    print(f"Configured channels: {', '.join(configured)}")

    sample = [
        Signal(
            symbol="TEST.NS",
            action="BUY",
            score=2.5,
            price=1234.56,
            reasons=[
                "This is a TEST alert from the stock monitoring agent.",
                "If you can read this, your alert channel works ✅",
            ],
            metrics={"rsi": 28.4},
        )
    ]
    as_of = datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")
    status = dispatch(secrets, sample, as_of)
    print(f"Dispatch status: {status}")

    ok = any(status.get(ch) for ch in configured)
    if ok:
        print("✅ At least one channel delivered. Check your inbox / Telegram.")
        return 0
    print("❌ No channel delivered. Re-check credentials (see error logs above).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
