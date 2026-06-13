"""Tests for the signal-generation logic."""
import numpy as np
import pandas as pd

from src.config import load_config
from src.signals import analyze


def _make_df(close_values):
    values = np.asarray(close_values, dtype=float)
    idx = pd.date_range(end="2024-01-01", periods=len(values), freq="D")
    return pd.DataFrame({"Close": values}, index=idx)


def test_strong_uptrend_is_not_sell():
    cfg = load_config()
    # Steady long uptrend -> should be BUY or HOLD, never SELL.
    close = pd.Series(np.linspace(100, 300, 260))
    sig = analyze("TEST.NS", _make_df(close), cfg)
    assert sig.action in {"BUY", "HOLD"}
    assert sig.symbol == "TEST.NS"


def test_strong_downtrend_is_not_buy():
    cfg = load_config()
    close = pd.Series(np.linspace(300, 100, 260))
    sig = analyze("TEST.NS", _make_df(close), cfg)
    assert sig.action in {"SELL", "HOLD"}


def test_oversold_crash_triggers_buy_votes():
    cfg = load_config()
    # Long flat then a sharp crash -> low RSI, below lower BB -> bullish votes.
    flat = np.full(240, 200.0)
    crash = np.linspace(200, 120, 20)
    close = pd.Series(np.concatenate([flat, crash]))
    sig = analyze("TEST.NS", _make_df(close), cfg)
    assert sig.metrics["rsi"] < 50
    # At least one bullish reason should be present.
    assert any("oversold" in r.lower() or "lower bollinger" in r.lower() for r in sig.reasons)


def test_signal_has_required_fields():
    cfg = load_config()
    close = pd.Series(100 + np.cumsum(np.random.default_rng(3).normal(0, 2, 260)))
    sig = analyze("TEST.NS", _make_df(close), cfg)
    assert sig.action in {"BUY", "SELL", "HOLD"}
    assert isinstance(sig.score, float)
    assert sig.price > 0
    assert "price" in sig.metrics
