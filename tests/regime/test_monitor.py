from datetime import date
from unittest.mock import MagicMock

import pandas as pd

from src.regime.fred_client import FREDClient
from src.regime.monitor import get_regime_series, get_regime_signal


def _make_client(values: list[float], dates: list[str]) -> FREDClient:
    client = MagicMock(spec=FREDClient)
    client.fetch_composite_spread.return_value = pd.Series(
        values,
        index=pd.to_datetime(dates),
        dtype="float64",
    )
    return client


def test_spread_2_0_returns_green() -> None:
    client = _make_client([2.0], ["2020-01-02"])
    assert get_regime_signal(client=client) == "GREEN"


def test_spread_3_0_returns_yellow() -> None:
    client = _make_client([3.0], ["2020-01-02"])
    assert get_regime_signal(client=client) == "YELLOW"


def test_spread_4_0_returns_red() -> None:
    client = _make_client([4.0], ["2020-01-02"])
    assert get_regime_signal(client=client) == "RED"


def test_boundary_2_50_is_yellow() -> None:
    client = _make_client([2.50], ["2020-01-02"])
    assert get_regime_signal(client=client) == "YELLOW"


def test_boundary_3_50_is_yellow() -> None:
    client = _make_client([3.50], ["2020-01-02"])
    assert get_regime_signal(client=client) == "YELLOW"


def test_as_of_does_not_look_ahead() -> None:
    # Jan 2 spread 2.0 (GREEN), Jan 6 spread 4.0 (RED).
    # as_of Jan 4 must use Jan 2 value — never see Jan 6.
    client = _make_client([2.0, 4.0], ["2020-01-02", "2020-01-06"])
    result = get_regime_signal(as_of=date(2020, 1, 4), client=client)
    assert result == "GREEN"


def test_get_regime_series_forward_fills() -> None:
    # 5 sparse data points over 22 business days; every bday must be filled.
    dates = ["2020-01-02", "2020-01-08", "2020-01-15", "2020-01-22", "2020-01-29"]
    values = [2.0, 4.0, 3.0, 2.0, 3.5]
    client = _make_client(values, dates)

    result = get_regime_series(start=date(2020, 1, 2), end=date(2020, 1, 31), client=client)

    bdays = pd.bdate_range("2020-01-02", "2020-01-31")
    assert result.reindex(bdays).isna().sum() == 0

    assert result[pd.Timestamp("2020-01-02")] == "GREEN"   # from data (2.0)
    assert result[pd.Timestamp("2020-01-03")] == "GREEN"   # ffill from Jan 2
    assert result[pd.Timestamp("2020-01-08")] == "RED"     # from data (4.0)
    assert result[pd.Timestamp("2020-01-09")] == "RED"     # ffill from Jan 8
    assert result[pd.Timestamp("2020-01-15")] == "YELLOW"  # from data (3.0)
