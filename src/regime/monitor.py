# Credit-spread regime signal using Moody's Baa corporate yield minus the
# 10-year Treasury (BAA - GS10).  This freely available FRED composite
# replaces BAMLH0A0HYM2 (ICE-restricted to 3 years of history since 2023)
# and BAA10Y (discontinued).  BAA is available from 1919; GS10 from 1953,
# giving full history through every major stress event.
import logging
from datetime import date
from typing import Literal

import pandas as pd  # type: ignore[import-untyped]

from src.regime.fred_client import FREDClient

logger = logging.getLogger(__name__)


def _classify(spread: float) -> Literal["GREEN", "YELLOW", "RED"]:
    if spread > 3.50:
        return "RED"
    if spread >= 2.50:
        return "YELLOW"
    return "GREEN"


def get_regime_signal(
    as_of: date | None = None,
    client: FREDClient | None = None,
) -> Literal["GREEN", "YELLOW", "RED"]:
    if client is None:
        client = FREDClient.from_settings()

    series = client.fetch_composite_spread().dropna()

    if as_of is None:
        spread = float(series.iloc[-1])
    else:
        as_of_ts = pd.Timestamp(as_of)
        eligible = series[series.index <= as_of_ts]
        spread = float(eligible.iloc[-1])

    logger.debug("BAA spread=%.2f → %s", spread, _classify(spread))
    return _classify(spread)


def get_regime_series(
    start: date,
    end: date,
    client: FREDClient | None = None,
) -> pd.Series:
    if client is None:
        client = FREDClient.from_settings()

    # Fetch with a 10-bday lookback so ffill always has a prior value at `start`
    fetch_start = (pd.Timestamp(start) - pd.offsets.BDay(10)).date()
    raw = client.fetch_composite_spread(start=fetch_start, end=end).dropna()
    regimes = raw.map(_classify)

    bdays = pd.bdate_range(start, end)
    return regimes.reindex(bdays).ffill().astype(object)


if __name__ == "__main__":
    print(get_regime_signal())
