"""Tests for technical indicator calculations."""
import numpy as np
import pandas as pd

from src import indicators as ta


def test_rsi_all_gains_is_100():
    close = pd.Series(np.arange(1, 30, dtype=float))
    r = ta.rsi(close, period=14)
    assert r.iloc[-1] == 100.0


def test_rsi_all_losses_is_zero():
    close = pd.Series(np.arange(30, 1, -1, dtype=float))
    r = ta.rsi(close, period=14)
    assert r.iloc[-1] == 0.0


def test_rsi_bounds():
    rng = np.random.default_rng(42)
    close = pd.Series(100 + np.cumsum(rng.normal(0, 1, 200)))
    r = ta.rsi(close, period=14).dropna()
    assert (r >= 0).all() and (r <= 100).all()


def test_sma_value():
    close = pd.Series([1, 2, 3, 4, 5], dtype=float)
    s = ta.sma(close, 3)
    assert s.iloc[-1] == 4.0  # mean of 3,4,5
    assert pd.isna(s.iloc[0])


def test_ema_recent_weight():
    close = pd.Series([10, 10, 10, 10, 20], dtype=float)
    e = ta.ema(close, 3)
    # EMA reacts to the jump but stays below the latest value.
    assert 10 < e.iloc[-1] < 20


def test_macd_columns_and_hist():
    close = pd.Series(100 + np.cumsum(np.random.default_rng(1).normal(0, 1, 100)))
    m = ta.macd(close)
    assert set(m.columns) == {"macd", "signal", "hist"}
    last = m.dropna().iloc[-1]
    assert np.isclose(last["hist"], last["macd"] - last["signal"])


def test_bollinger_ordering():
    close = pd.Series(100 + np.cumsum(np.random.default_rng(2).normal(0, 1, 100)))
    bb = ta.bollinger_bands(close, 20, 2.0).dropna()
    assert (bb["bb_upper"] >= bb["bb_middle"]).all()
    assert (bb["bb_middle"] >= bb["bb_lower"]).all()
