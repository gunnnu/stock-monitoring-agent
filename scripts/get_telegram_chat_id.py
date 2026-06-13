#!/usr/bin/env python3
"""Helper: find your Telegram chat id.

Usage:
  1. Create a bot with @BotFather and copy its token.
  2. Open a chat with your new bot and send it any message (e.g. "hi").
     (For a group, add the bot to the group and send a message there.)
  3. Run:  TELEGRAM_BOT_TOKEN=<token> python scripts/get_telegram_chat_id.py

It prints every chat id the bot can currently see.
"""
import os
import sys

import requests


def main() -> int:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("ERROR: set TELEGRAM_BOT_TOKEN first, e.g.:")
        print("  TELEGRAM_BOT_TOKEN=123:ABC python scripts/get_telegram_chat_id.py")
        return 1

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except Exception as exc:
        print(f"Request failed: {exc}")
        return 1

    data = resp.json()
    if not data.get("ok"):
        print(f"Telegram API error: {data}")
        return 1

    results = data.get("result", [])
    if not results:
        print("No updates found. Send your bot a message first, then re-run.")
        print("(If you only just messaged it, wait a few seconds and retry.)")
        return 0

    seen = {}
    for upd in results:
        msg = upd.get("message") or upd.get("channel_post") or {}
        chat = msg.get("chat", {})
        cid = chat.get("id")
        if cid is not None and cid not in seen:
            title = chat.get("title") or chat.get("username") or chat.get("first_name", "")
            seen[cid] = (chat.get("type", "?"), title)

    print("Found chat id(s):")
    for cid, (ctype, name) in seen.items():
        print(f"  TELEGRAM_CHAT_ID={cid}   ({ctype}: {name})")
    print("\nAdd the id you want as the TELEGRAM_CHAT_ID secret.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
