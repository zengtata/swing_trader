from datetime import date

import pandas as pd
import pytest

from src.regime.fred_client import FREDClient, FREDFetchError


@pytest.fixture
def client() -> FREDClient:
    return FREDClient(api_key="test-key")


def test_fetch_series_drops_nan(mocker, client: FREDClient) -> None:
    raw = pd.Series(
        [1.0, float("nan"), 3.0],
        index=pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"]),
        dtype="float64",
    )
    mocker.patch("fredapi.Fred.get_series", return_value=raw)

    result = client.fetch_series("UNRATE")

    assert len(result) == 2
    assert not result.isna().any()


def test_fetch_series_raises_fred_fetch_error_and_chains_cause(mocker, client: FREDClient) -> None:
    original = ValueError("network timeout")
    mocker.patch("fredapi.Fred.get_series", side_effect=original)

    with pytest.raises(FREDFetchError) as exc_info:
        client.fetch_series("UNRATE")

    assert exc_info.value.__cause__ is original


def test_fetch_series_cache_returns_same_object(mocker) -> None:
    raw = pd.Series(
        [1.0, 2.0],
        index=pd.to_datetime(["2020-01-01", "2020-01-02"]),
        dtype="float64",
    )
    mock_get = mocker.patch("fredapi.Fred.get_series", return_value=raw)
    client = FREDClient(api_key="test-key")

    result1 = client.fetch_series("UNRATE", start=date(2020, 1, 1))
    result2 = client.fetch_series("UNRATE", start=date(2020, 1, 1))

    assert result1 is result2
    mock_get.assert_called_once()


def test_fetch_composite_spread_returns_baa_minus_gs10(mocker) -> None:
    baa = pd.Series(
        [5.0, 5.2],
        index=pd.to_datetime(["2020-01-02", "2020-01-03"]),
        dtype="float64",
    )
    gs10 = pd.Series(
        [2.8, 3.0],
        index=pd.to_datetime(["2020-01-02", "2020-01-03"]),
        dtype="float64",
    )

    def _fake_get_series(series_id, **_kwargs):
        return {"DBAA": baa, "DGS10": gs10}[series_id]

    mocker.patch("fredapi.Fred.get_series", side_effect=_fake_get_series)
    client = FREDClient(api_key="test-key")

    result = client.fetch_composite_spread()

    pd.testing.assert_series_equal(
        result,
        pd.Series(
            [2.2, 2.2],
            index=pd.to_datetime(["2020-01-02", "2020-01-03"]),
            dtype="float64",
            name="BAA_spread",
        ),
        check_exact=False,
        atol=1e-9,
    )


def test_fetch_composite_spread_drops_dates_missing_from_either_series(mocker) -> None:
    baa = pd.Series(
        [5.0, 5.2],
        index=pd.to_datetime(["2020-01-02", "2020-01-03"]),
        dtype="float64",
    )
    gs10 = pd.Series(
        [2.8],
        index=pd.to_datetime(["2020-01-02"]),
        dtype="float64",
    )

    def _fake_get_series(series_id, **_kwargs):
        return {"DBAA": baa, "DGS10": gs10}[series_id]

    mocker.patch("fredapi.Fred.get_series", side_effect=_fake_get_series)
    client = FREDClient(api_key="test-key")

    result = client.fetch_composite_spread()

    assert len(result) == 1
    assert result.index[0] == pd.Timestamp("2020-01-02")


def test_fetch_composite_spread_result_is_named_baa_spread(mocker) -> None:
    raw = pd.Series(
        [5.0],
        index=pd.to_datetime(["2020-01-02"]),
        dtype="float64",
    )
    mocker.patch("fredapi.Fred.get_series", return_value=raw)
    client = FREDClient(api_key="test-key")

    result = client.fetch_composite_spread()

    assert result.name == "BAA_spread"


def test_fetch_composite_spread_propagates_fred_fetch_error(mocker) -> None:
    mocker.patch("fredapi.Fred.get_series", side_effect=Exception("timeout"))
    client = FREDClient(api_key="test-key")
    with pytest.raises(FREDFetchError):
        client.fetch_composite_spread()
