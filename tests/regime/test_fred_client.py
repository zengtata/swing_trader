import pandas as pd
import pytest

from src.regime.fred_client import FREDClient, FREDFetchError


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
        return {"BAA": baa, "GS10": gs10}[series_id]

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
        return {"BAA": baa, "GS10": gs10}[series_id]

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
