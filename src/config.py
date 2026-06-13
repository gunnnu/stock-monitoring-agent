"""Configuration loading for the stock monitoring agent."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


def load_config(path: str | os.PathLike | None = None) -> Dict[str, Any]:
    """Load the YAML configuration file.

    The path can be overridden with the ``CONFIG_PATH`` environment variable
    or by passing ``path`` explicitly.
    """
    cfg_path = Path(path or os.environ.get("CONFIG_PATH") or DEFAULT_CONFIG_PATH)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found: {cfg_path}")
    with cfg_path.open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}
    return config


def get_secrets() -> Dict[str, str | None]:
    """Read alerting credentials from environment variables / GitHub secrets."""
    return {
        # Email (SMTP)
        "smtp_host": os.environ.get("SMTP_HOST"),
        "smtp_port": os.environ.get("SMTP_PORT", "587"),
        "smtp_user": os.environ.get("SMTP_USER"),
        "smtp_password": os.environ.get("SMTP_PASSWORD"),
        "email_from": os.environ.get("EMAIL_FROM") or os.environ.get("SMTP_USER"),
        "email_to": os.environ.get("EMAIL_TO"),
        # Telegram
        "telegram_bot_token": os.environ.get("TELEGRAM_BOT_TOKEN"),
        "telegram_chat_id": os.environ.get("TELEGRAM_CHAT_ID"),
    }
