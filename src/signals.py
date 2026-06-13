"""Combine technical indicators into a BUY / SELL / HOLD signal per stock."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

import pandas as pd

from . import indicators as ta


@dataclass
class Signal:
    symbol: str
    action: str               # BUY / SELL / HOLD
    score: float              # net weighted score
    price: float
    reasons: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)


def _crossed_up(series: pd.Series) -> bool:
    """True if series went from <=0 to >0 on the last bar."""
    if len(series.dropna()) < 2:
        return False
    prev, last = series.iloc[-2], series.iloc[-1]
    return prev <= 0 < last


def _crossed_down(series: pd.Series) -> bool:
    if len(series.dropna()) < 2:
        return False
    prev, last = series.iloc[-2], series.iloc[-1]
    return prev >= 0 > last


def analyze(symbol: str, df: pd.DataFrame, config: Dict[str, Any]) -> Signal:
    """Run the indicator suite over ``df`` and produce a Signal.

    ``df`` must contain at least a ``Close`` column indexed by date.
    """
    ind_cfg = config.get("indicators", {})
    sig_cfg = config.get("signal", {})
    weights = sig_cfg.get("weights", {})

    close = df["Close"].astype(float)
    price = float(close.iloc[-1])

    reasons: List[str] = []
    metrics: Dict[str, float] = {"price": price}
    score = 0.0

    # ---- RSI ---------------------------------------------------------
    rsi_series = ta.rsi(close, ind_cfg.get("rsi_period", 14))
    rsi_val = rsi_series.iloc[-1]
    if pd.notna(rsi_val):
        metrics["rsi"] = round(float(rsi_val), 2)
        w = weights.get("rsi", 1.0)
        if rsi_val < ind_cfg.get("rsi_oversold", 30):
            score += w
            reasons.append(f"RSI {rsi_val:.1f} oversold (<{ind_cfg.get('rsi_oversold', 30)}) → bullish")
        elif rsi_val > ind_cfg.get("rsi_overbought", 70):
            score -= w
            reasons.append(f"RSI {rsi_val:.1f} overbought (>{ind_cfg.get('rsi_overbought', 70)}) → bearish")

    # ---- SMA golden/death cross -------------------------------------
    sma_s = ta.sma(close, ind_cfg.get("sma_short", 50))
    sma_l = ta.sma(close, ind_cfg.get("sma_long", 200))
    sma_diff = sma_s - sma_l
    if sma_diff.notna().sum() >= 2:
        w = weights.get("sma_cross", 1.5)
        metrics["sma_short"] = round(float(sma_s.iloc[-1]), 2)
        metrics["sma_long"] = round(float(sma_l.iloc[-1]), 2)
        if _crossed_up(sma_diff):
            score += w
            reasons.append("Golden cross: short SMA crossed above long SMA → bullish")
        elif _crossed_down(sma_diff):
            score -= w
            reasons.append("Death cross: short SMA crossed below long SMA → bearish")
        elif sma_diff.iloc[-1] > 0:
            # Sustained uptrend, smaller contribution
            score += w * 0.25
            reasons.append("Price trend: short SMA above long SMA (uptrend)")
        elif sma_diff.iloc[-1] < 0:
            score -= w * 0.25
            reasons.append("Price trend: short SMA below long SMA (downtrend)")

    # ---- MACD crossover ---------------------------------------------
    macd_df = ta.macd(
        close,
        ind_cfg.get("macd_fast", 12),
        ind_cfg.get("macd_slow", 26),
        ind_cfg.get("macd_signal", 9),
    )
    macd_hist = macd_df["hist"]
    if macd_hist.notna().sum() >= 2:
        w = weights.get("macd", 1.0)
        metrics["macd_hist"] = round(float(macd_hist.iloc[-1]), 3)
        if _crossed_up(macd_hist):
            score += w
            reasons.append("MACD bullish crossover (MACD crossed above signal)")
        elif _crossed_down(macd_hist):
            score -= w
            reasons.append("MACD bearish crossover (MACD crossed below signal)")

    # ---- Bollinger Bands --------------------------------------------
    bb = ta.bollinger_bands(
        close,
        ind_cfg.get("bb_period", 20),
        float(ind_cfg.get("bb_std", 2.0)),
    )
    bb_lower = bb["bb_lower"].iloc[-1]
    bb_upper = bb["bb_upper"].iloc[-1]
    if pd.notna(bb_lower) and pd.notna(bb_upper):
        w = weights.get("bollinger", 1.0)
        metrics["bb_lower"] = round(float(bb_lower), 2)
        metrics["bb_upper"] = round(float(bb_upper), 2)
        if price <= bb_lower:
            score += w
            reasons.append("Price at/below lower Bollinger Band → potentially oversold")
        elif price >= bb_upper:
            score -= w
            reasons.append("Price at/above upper Bollinger Band → potentially overbought")

    # ---- EMA short-term trend ---------------------------------------
    ema_s = ta.ema(close, ind_cfg.get("ema_short", 12))
    ema_l = ta.ema(close, ind_cfg.get("ema_long", 26))
    if pd.notna(ema_s.iloc[-1]) and pd.notna(ema_l.iloc[-1]):
        w = weights.get("ema_trend", 0.5)
        if ema_s.iloc[-1] > ema_l.iloc[-1]:
            score += w
            reasons.append("Short EMA above long EMA (short-term uptrend)")
        else:
            score -= w
            reasons.append("Short EMA below long EMA (short-term downtrend)")

    # ---- Decision ----------------------------------------------------
    buy_th = sig_cfg.get("buy_threshold", 1.5)
    sell_th = sig_cfg.get("sell_threshold", -1.5)
    if score >= buy_th:
        action = "BUY"
    elif score <= sell_th:
        action = "SELL"
    else:
        action = "HOLD"

    return Signal(
        symbol=symbol,
        action=action,
        score=round(score, 2),
        price=round(price, 2),
        reasons=reasons,
        metrics=metrics,
    )
