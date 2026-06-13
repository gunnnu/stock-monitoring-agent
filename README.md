# 📈 Indian Stock Monitoring Agent

An automated agent that monitors Indian stocks (NSE/BSE) on a schedule using
**GitHub Actions**, computes technical indicators, and sends **BUY / SELL**
alerts via **Email** and/or **Telegram**.

> ⚠️ **Disclaimer:** This project generates signals from technical indicators
> for **educational purposes only**. It is **not financial advice**. Markets are
> risky — always do your own research before trading.

---

## How it works

On each scheduled run the agent:

1. **Fetches** ~1 year of daily price history for every stock in your watchlist
   (via [`yfinance`](https://pypi.org/project/yfinance/)).
2. **Computes** technical indicators for each stock:
   - **RSI (14)** — overbought / oversold momentum
   - **SMA 50 / 200** — golden cross (bullish) & death cross (bearish)
   - **MACD (12/26/9)** — momentum crossovers
   - **Bollinger Bands (20, 2σ)** — mean-reversion extremes
   - **EMA 12 / 26** — short-term trend
3. **Scores** each stock with a weighted vote across indicators and decides
   **BUY**, **SELL**, or **HOLD**.
4. **Alerts** you via Email and/or Telegram for actionable signals, with the
   reasons behind each call.

```
watchlist ─▶ data.py (yfinance) ─▶ indicators.py ─▶ signals.py ─▶ alerts.py
                                                                   ├─ Email (SMTP)
                                                                   └─ Telegram
```

---

## Quick start

### 1. Use this repository
The agent runs entirely on GitHub Actions — no server needed. Just configure
secrets and it runs on schedule.

### 2. Configure alert channels (GitHub Secrets)

Go to **Settings → Secrets and variables → Actions → New repository secret** and
add the ones you want. You can enable **email, Telegram, or both**.

**Email (SMTP)** — e.g. Gmail with an [App Password](https://support.google.com/accounts/answer/185833):

| Secret | Example | Notes |
| --- | --- | --- |
| `SMTP_HOST` | `smtp.gmail.com` | |
| `SMTP_PORT` | `587` | `465` for SSL, `587` for STARTTLS |
| `SMTP_USER` | `you@gmail.com` | |
| `SMTP_PASSWORD` | `app-password` | **Not** your login password |
| `EMAIL_FROM` | `you@gmail.com` | optional (defaults to `SMTP_USER`) |
| `EMAIL_TO` | `you@gmail.com,friend@x.com` | comma-separated for multiple |

**Telegram:**

| Secret | How to get it |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | Create a bot with [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | Message your bot, then check `https://api.telegram.org/bot<TOKEN>/getUpdates`, or use [@userinfobot](https://t.me/userinfobot) |

> If no channel is configured the agent still runs and logs signals to the
> Actions console — it just won't send anything.

### 3. Customize your watchlist

Edit [`config.yaml`](config.yaml). Use NSE tickers (`.NS`) or BSE tickers (`.BO`):

```yaml
watchlist:
  - RELIANCE.NS
  - TCS.NS
  - HDFCBANK.NS
```

You can also tune indicator parameters and the buy/sell score thresholds there.

### 4. Run it

- **Automatically:** the [workflow](.github/workflows/stock-monitor.yml) runs on a
  cron schedule aligned to NSE trading hours (mid-morning, pre-close, and after
  the daily close, Mon–Fri).
- **Manually:** go to the **Actions** tab → **Indian Stock Monitor** → **Run workflow**.

---

## Run locally

```bash
pip install -r requirements.txt

# Optional: set alert env vars (see .env.example), otherwise it just prints to console
export TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=...

python -m src.main
```

Run the tests:

```bash
pip install pytest
python -m pytest -q
```

---

## Configuration reference

All behavior is driven by [`config.yaml`](config.yaml):

| Section | Purpose |
| --- | --- |
| `watchlist` | Stocks to monitor (NSE `.NS` / BSE `.BO`) |
| `history_period`, `interval` | How much data to fetch and candle size |
| `indicators` | Periods/thresholds for RSI, SMA, EMA, MACD, Bollinger |
| `signal.weights` | Relative importance of each indicator's vote |
| `signal.buy_threshold` / `sell_threshold` | Score cutoffs for BUY / SELL |
| `alerts.notify_on` | Which actions trigger alerts (default BUY & SELL) |
| `alerts.send_empty_digest` | Send a digest even when there are no signals |

---

## Tuning the signal logic

Each indicator casts a weighted vote in `[-weight .. +weight]`. The votes are
summed into a **score**; `score ≥ buy_threshold` → **BUY**,
`score ≤ sell_threshold` → **SELL**, otherwise **HOLD**. Raise the thresholds for
fewer, higher-conviction alerts; lower them to be more sensitive. Adjust
`signal.weights` to emphasize the indicators you trust most.

---

## Project layout

```
.github/workflows/stock-monitor.yml   # scheduled GitHub Actions workflow
config.yaml                           # watchlist + indicator/signal settings
src/
  config.py        # load config + read secrets from env
  data.py          # fetch price history via yfinance
  indicators.py    # RSI, SMA, EMA, MACD, Bollinger (pandas only)
  signals.py       # combine indicators into BUY/SELL/HOLD
  alerts.py        # email (SMTP) + Telegram delivery
  main.py          # orchestration / entry point
tests/             # unit tests for indicators & signals
```

---

## Notes & limitations

- **Data source:** free Yahoo Finance data via `yfinance`. It can occasionally be
  rate-limited or delayed; the agent skips failed tickers rather than aborting.
- **GitHub cron timing:** scheduled Actions can be delayed by several minutes
  during peak load — fine for daily-signal monitoring, not for tick-level trading.
- **Not financial advice.** See the disclaimer at the top.
