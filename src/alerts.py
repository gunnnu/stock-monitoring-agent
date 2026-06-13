"""Alert delivery via email (SMTP) and Telegram."""
from __future__ import annotations

import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List

import requests

from .signals import Signal

log = logging.getLogger(__name__)

ACTION_EMOJI = {"BUY": "🟢", "SELL": "🔴", "HOLD": "⚪"}


# ---------------------------------------------------------------------------
# Message formatting
# ---------------------------------------------------------------------------
def format_plaintext(signals: List[Signal], as_of: str) -> str:
    lines = [f"📊 Indian Stock Monitor — {as_of}", ""]
    if not signals:
        lines.append("No actionable signals at this time.")
        return "\n".join(lines)

    for s in signals:
        emoji = ACTION_EMOJI.get(s.action, "")
        lines.append(f"{emoji} {s.action}  {s.symbol}  @ ₹{s.price}  (score {s.score})")
        for r in s.reasons:
            lines.append(f"    • {r}")
        lines.append("")
    lines.append("⚠️ Educational signals only — not financial advice. Do your own research.")
    return "\n".join(lines)


def format_html(signals: List[Signal], as_of: str) -> str:
    rows = []
    for s in signals:
        color = {"BUY": "#16a34a", "SELL": "#dc2626", "HOLD": "#6b7280"}.get(s.action, "#000")
        reasons = "".join(f"<li>{r}</li>" for r in s.reasons)
        rows.append(
            f"""
            <tr>
              <td style="padding:8px;font-weight:bold;color:{color};">{ACTION_EMOJI.get(s.action,'')} {s.action}</td>
              <td style="padding:8px;font-weight:bold;">{s.symbol}</td>
              <td style="padding:8px;">₹{s.price}</td>
              <td style="padding:8px;">{s.score}</td>
              <td style="padding:8px;"><ul style="margin:0;padding-left:18px;">{reasons}</ul></td>
            </tr>"""
        )
    table = "".join(rows) if rows else (
        '<tr><td colspan="5" style="padding:8px;">No actionable signals.</td></tr>'
    )
    return f"""\
    <html><body style="font-family:Arial,Helvetica,sans-serif;">
      <h2>📊 Indian Stock Monitor — {as_of}</h2>
      <table style="border-collapse:collapse;width:100%;">
        <thead>
          <tr style="background:#f3f4f6;text-align:left;">
            <th style="padding:8px;">Action</th><th style="padding:8px;">Symbol</th>
            <th style="padding:8px;">Price</th><th style="padding:8px;">Score</th>
            <th style="padding:8px;">Reasons</th>
          </tr>
        </thead>
        <tbody>{table}</tbody>
      </table>
      <p style="color:#6b7280;font-size:12px;margin-top:16px;">
        ⚠️ Educational signals only — not financial advice. Do your own research.
      </p>
    </body></html>"""


# ---------------------------------------------------------------------------
# Channels
# ---------------------------------------------------------------------------
def send_email(secrets: Dict[str, str | None], subject: str, text: str, html: str) -> bool:
    host = secrets.get("smtp_host")
    user = secrets.get("smtp_user")
    password = secrets.get("smtp_password")
    email_to = secrets.get("email_to")
    email_from = secrets.get("email_from")

    if not (host and user and password and email_to):
        log.info("Email not configured (missing SMTP settings) — skipping email alert.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = email_from or user
    msg["To"] = email_to
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    port = int(secrets.get("smtp_port") or 587)
    recipients = [addr.strip() for addr in email_to.split(",") if addr.strip()]

    try:
        if port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, context=context) as server:
                server.login(user, password)
                server.sendmail(msg["From"], recipients, msg.as_string())
        else:
            with smtplib.SMTP(host, port) as server:
                server.starttls(context=ssl.create_default_context())
                server.login(user, password)
                server.sendmail(msg["From"], recipients, msg.as_string())
        log.info("Email alert sent to %s", email_to)
        return True
    except Exception as exc:
        log.error("Failed to send email: %s", exc)
        return False


def send_telegram(secrets: Dict[str, str | None], text: str) -> bool:
    token = secrets.get("telegram_bot_token")
    chat_id = secrets.get("telegram_chat_id")
    if not (token and chat_id):
        log.info("Telegram not configured (missing token/chat id) — skipping Telegram alert.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    # Telegram messages cap at 4096 chars.
    payload = {
        "chat_id": chat_id,
        "text": text[:4096],
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, data=payload, timeout=30)
        resp.raise_for_status()
        log.info("Telegram alert sent to chat %s", chat_id)
        return True
    except Exception as exc:
        log.error("Failed to send Telegram message: %s", exc)
        return False


def dispatch(secrets: Dict[str, str | None], signals: List[Signal], as_of: str) -> Dict[str, bool]:
    """Send the digest over all configured channels. Returns per-channel status."""
    text = format_plaintext(signals, as_of)
    html = format_html(signals, as_of)
    n = len(signals)
    subject = f"📈 Stock Monitor: {n} signal(s) — {as_of}" if n else f"Stock Monitor digest — {as_of}"
    return {
        "email": send_email(secrets, subject, text, html),
        "telegram": send_telegram(secrets, text),
    }
