"""Fetch historical price data for Indian stocks via yfinance."""
from __future__ import annotations

import logging
from typing import Dict, List

import pandas as pd
import yfinance as yf

log = logging.getLogger(__name__)


def fetch_history(
    symbols: List[str],
    period: str = "1y",
    interval: str = "1d",
) -> Dict[str, pd.DataFrame]:
    """Download OHLCV history for each symbol.

    Returns a mapping ``symbol -> DataFrame``. Symbols that fail to download
    or return empty data are skipped (with a warning) so one bad ticker does
    not abort the whole run.
    """
    results: Dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        try:
            df = yf.download(
                symbol,
                period=period,
                interval=interval,
                auto_adjust=True,
                progress=False,
                threads=False,
            )
        except Exception as exc:  # network / API hiccups
            log.warning("Failed to download %s: %s", symbol, exc)
            continue

        if df is None or df.empty:
            log.warning("No data returned for %s", symbol)
            continue

        # yfinance may return MultiIndex columns when given a single ticker
        # in newer versions; flatten to simple column names.
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.dropna(subset=["Close"])
        if df.empty:
            log.warning("All-NaN close for %s", symbol)
            continue

        results[symbol] = df
    return results
