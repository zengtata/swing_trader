# BAA-GS10 Composite Spread Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the ICE-restricted BAMLH0A0HYM2 / BAA10Y FRED series with a freely available composite spread (BAA − GS10) that has full history back to 1953, and update all callers and tests to use it.

**Architecture:** Add `fetch_composite_spread()` to `FREDClient` that fetches BAA and GS10 independently then inner-joins on date and returns BAA − GS10 as a named Series. `monitor.py` calls this new method instead of the single-series `fetch_series()`. Thresholds remain GREEN < 2.50 / YELLOW 2.50–3.50 / RED > 3.50 (already correct in monitor.py). The validation notebook is updated to match the new fetch logic.

**Tech Stack:** Python 3.11, pandas, fredapi, pytest, pytest-mock, nbformat

---

## File Map

| File | Action | What changes |
|---|---|---|
| `src/regime/fred_client.py` | Modify | Add `fetch_composite_spread()` |
| `src/regime/monitor.py` | Modify | Remove `_SERIES_ID`, call `fetch_composite_spread()`, update log/comment |
| `tests/regime/test_fred_client.py` | Modify | Add tests for `fetch_composite_spread()` |
| `tests/regime/test_monitor.py` | Modify | Mock `fetch_composite_spread` instead of `fetch_series` |
| `notebooks/01_regime_validation.ipynb` | Modify | Fetch BAA+GS10, compute composite, update chart labels |

---

## Task 1: Add `fetch_composite_spread()` to FREDClient

**Files:**
- Modify: `src/regime/fred_client.py`
- Test: `tests/regime/test_fred_client.py`

- [ ] **Step 1: Write three failing tests**

Append to `tests/regime/test_fred_client.py`:

```python
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
    # BAA has Jan 2 and Jan 3; GS10 only has Jan 2.
    # Inner-join must drop Jan 3 because GS10 is missing it.
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/regime/test_fred_client.py::test_fetch_composite_spread_returns_baa_minus_gs10 tests/regime/test_fred_client.py::test_fetch_composite_spread_drops_dates_missing_from_either_series tests/regime/test_fred_client.py::test_fetch_composite_spread_result_is_named_baa_spread -v
```

Expected: `AttributeError: 'FREDClient' object has no attribute 'fetch_composite_spread'`

- [ ] **Step 3: Implement `fetch_composite_spread()` in `src/regime/fred_client.py`**

The full file after the edit (replace everything):

```python
import logging
from datetime import date

import fredapi  # type: ignore[import-untyped]
import pandas as pd  # type: ignore[import-untyped]

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class FREDFetchError(Exception):
    pass


class FREDClient:
    def __init__(self, api_key: str) -> None:
        self._fred = fredapi.Fred(api_key=api_key)
        self._cache: dict[tuple[str, date | None, date | None], pd.Series] = {}

    @classmethod
    def from_settings(cls) -> "FREDClient":
        return cls(api_key=get_settings().fred_api_key)

    def fetch_series(
        self,
        series_id: str,
        start: date | None = None,
        end: date | None = None,
    ) -> pd.Series:
        key = (series_id, start, end)
        if key in self._cache:
            return self._cache[key]

        try:
            raw: pd.Series = self._fred.get_series(
                series_id,
                observation_start=start,
                observation_end=end,
            )
        except Exception as exc:
            raise FREDFetchError(f"Failed to fetch FRED series {series_id!r}") from exc

        result = raw.dropna().astype("float64")
        result.index = pd.to_datetime(result.index)
        self._cache[key] = result
        return result

    def fetch_composite_spread(
        self,
        start: date | None = None,
        end: date | None = None,
    ) -> pd.Series:
        baa = self.fetch_series("BAA", start=start, end=end)
        gs10 = self.fetch_series("GS10", start=start, end=end)
        aligned = pd.DataFrame({"BAA": baa, "GS10": gs10}).dropna()
        spread = aligned["BAA"] - aligned["GS10"]
        spread.name = "BAA_spread"
        return spread
```

- [ ] **Step 4: Run tests to confirm they pass**

```
pytest tests/regime/test_fred_client.py -v
```

Expected: all 6 tests PASS (3 pre-existing + 3 new).

- [ ] **Step 5: Commit**

```bash
git add src/regime/fred_client.py tests/regime/test_fred_client.py
git commit -m "feat(regime): add fetch_composite_spread() computing BAA - GS10"
```

---

## Task 2: Update monitor.py to use `fetch_composite_spread()`

**Files:**
- Modify: `src/regime/monitor.py`
- Modify: `tests/regime/test_monitor.py`

- [ ] **Step 1: Update `tests/regime/test_monitor.py`**

The `_make_client()` helper currently mocks `client.fetch_series`. Change it to mock `client.fetch_composite_spread` so the monitor tests stay decoupled from which FRED series are fetched.

Replace the entire file with:

```python
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
```

- [ ] **Step 2: Run the monitor tests to confirm they now fail** (because monitor.py still calls `fetch_series`)

```
pytest tests/regime/test_monitor.py -v
```

Expected: failures because `monitor.py` calls `client.fetch_series(...)` but the mock only sets up `fetch_composite_spread`.

- [ ] **Step 3: Rewrite `src/regime/monitor.py`**

Replace the entire file with:

```python
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
```

- [ ] **Step 4: Run all regime tests**

```
pytest tests/regime/ -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/regime/monitor.py tests/regime/test_monitor.py
git commit -m "feat(regime): switch monitor to BAA-GS10 composite spread via fetch_composite_spread"
```

---

## Task 3: Update the validation notebook

**Files:**
- Modify: `notebooks/01_regime_validation.ipynb`

The notebook has 6 code cells. Only cells `cc000002` and `cc000004` reference the old series; the rest (SPY fetch, regime shading, event table, pass/fail) are series-agnostic and need no change.

- [ ] **Step 1: Replace cell cc000002 (raw fetch + spot-check)**

New content for that cell:

```python
START = date(2007, 1, 1)
END   = date(2024, 12, 31)

# ── Step 1: verify raw FRED data has historical RED-range values ──────────
_fetch_start = (pd.Timestamp(START) - pd.offsets.BDay(10)).date()
_client      = FREDClient.from_settings()

_baa  = _client.fetch_series('BAA',  start=_fetch_start, end=END)
_gs10 = _client.fetch_series('GS10', start=_fetch_start, end=END)

import pandas as pd as _pd  # already imported above — use the existing import
_aligned    = _pd.DataFrame({'BAA': _baa, 'GS10': _gs10}).dropna()
raw_spreads = _aligned['BAA'] - _aligned['GS10']
raw_spreads.name = 'BAA_spread'

print(f"Raw FRED composite: {len(raw_spreads):,} observations")
print(f"  date range : {raw_spreads.index[0].date()} → {raw_spreads.index[-1].date()}")
print(f"  min / max  : {raw_spreads.min():.2f} / {raw_spreads.max():.2f}")
n_red = int((raw_spreads > 3.50).sum())
print(f"  values > 3.50 (RED threshold): {n_red:,}  ← must be > 0 for GFC/COVID to appear")
if n_red == 0:
    raise RuntimeError(
        "FRED returned no RED-range values — check FRED_API_KEY "
        "and that historical data is being fetched."
    )

# ── Step 2: compute regime series (get_regime_series uses the same buffered fetch) ─
print()
print("Computing regime series...")
regimes = get_regime_series(start=START, end=END, client=_client)
regimes = regimes.ffill()

print()
print("Regime value_counts (dropna=False — NaN means alignment gap):")
print(regimes.value_counts(dropna=False).to_string())
print(f"NaN count : {regimes.isna().sum()}")

print()
print("Spot-checks — expect RED during GFC and COVID:")
for dt_str, note in [
    ('2008-10-13', 'GFC near peak'),
    ('2009-01-20', 'GFC trough period'),
    ('2020-03-23', 'COVID low'),
]:
    val = regimes.get(pd.Timestamp(dt_str), 'N/A')
    flag = '✓' if val == 'RED' else f'✗  UNEXPECTED ({val})'
    print(f"  {dt_str}  {note:<22}  {flag}")
```

Note: the `import pandas as pd as _pd` line above is a typo in the plan — the notebook already imports pandas as `pd`; just use `pd.DataFrame(...)` directly. The corrected cell source is:

```python
START = date(2007, 1, 1)
END   = date(2024, 12, 31)

_fetch_start = (pd.Timestamp(START) - pd.offsets.BDay(10)).date()
_client      = FREDClient.from_settings()

_baa  = _client.fetch_series('BAA',  start=_fetch_start, end=END)
_gs10 = _client.fetch_series('GS10', start=_fetch_start, end=END)
_aligned    = pd.DataFrame({'BAA': _baa, 'GS10': _gs10}).dropna()
raw_spreads = (_aligned['BAA'] - _aligned['GS10']).rename('BAA_spread')

print(f"Raw FRED composite: {len(raw_spreads):,} observations")
print(f"  date range : {raw_spreads.index[0].date()} → {raw_spreads.index[-1].date()}")
print(f"  min / max  : {raw_spreads.min():.2f} / {raw_spreads.max():.2f}")
n_red = int((raw_spreads > 3.50).sum())
print(f"  values > 3.50 (RED threshold): {n_red:,}  ← must be > 0 for GFC/COVID to appear")
if n_red == 0:
    raise RuntimeError(
        "FRED returned no RED-range values — check FRED_API_KEY "
        "and that historical data is being fetched."
    )

print()
print("Computing regime series...")
regimes = get_regime_series(start=START, end=END, client=_client)
regimes = regimes.ffill()

print()
print("Regime value_counts (dropna=False — NaN means alignment gap):")
print(regimes.value_counts(dropna=False).to_string())
print(f"NaN count : {regimes.isna().sum()}")

print()
print("Spot-checks — expect RED during GFC and COVID:")
for dt_str, note in [
    ('2008-10-13', 'GFC near peak'),
    ('2009-01-20', 'GFC trough period'),
    ('2020-03-23', 'COVID low'),
]:
    val = regimes.get(pd.Timestamp(dt_str), 'N/A')
    flag = '✓' if val == 'RED' else f'✗  UNEXPECTED ({val})'
    print(f"  {dt_str}  {note:<22}  {flag}")
```

- [ ] **Step 2: Replace cell cc000004 (chart) — update titles and legend labels only**

Change every occurrence of `BAA10Y` in the chart cell to `BAA-GS10 spread`. Specifically:

- `ax1.set_title(...)` → `'SPY Price with BAA-GS10 Spread Regime Signal  (2007-2024)'`
- `ax2.set_title(...)` → `'SPY Rolling Drawdown with BAA-GS10 Spread Regime Signal'`
- Legend label for green: `'GREEN - BAA-GS10 < 2.50'`
- Legend label for gold:  `'YELLOW - BAA-GS10 2.50 to 3.50'`
- Legend label for red:   `'RED - BAA-GS10 > 3.50'`

Full replacement source for cell cc000004:

```python
REGIME_COLORS = {'GREEN': 'green', 'YELLOW': 'gold', 'RED': 'red'}


def shade_regimes(ax, regime_series):
    current = None
    block_start = None
    for dt, val in regime_series.items():
        if pd.isna(val):
            continue
        if val != current:
            if current is not None:
                ax.axvspan(block_start, dt, alpha=0.2,
                           color=REGIME_COLORS[current], lw=0)
            current = val
            block_start = dt
    if current is not None:
        ax.axvspan(block_start, regime_series.index[-1], alpha=0.2,
                   color=REGIME_COLORS[current], lw=0)


fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(18, 10), sharex=True)

ax1.plot(spy.index, spy.values, color='black', linewidth=0.7, label='SPY Close')
shade_regimes(ax1, regimes)
ax1.set_ylabel('SPY Price ($)', fontsize=11)
ax1.set_title('SPY Price with BAA-GS10 Spread Regime Signal  (2007-2024)', fontsize=13)
ax1.legend(
    handles=[
        mpatches.Patch(color='green', alpha=0.5, label='GREEN - BAA-GS10 < 2.50'),
        mpatches.Patch(color='gold',  alpha=0.5, label='YELLOW - BAA-GS10 2.50 to 3.50'),
        mpatches.Patch(color='red',   alpha=0.5, label='RED - BAA-GS10 > 3.50'),
        plt.Line2D([0], [0], color='black', linewidth=0.7, label='SPY Close'),
    ],
    loc='upper left', fontsize=9,
)

ax2.fill_between(drawdown.index, drawdown.values, 0,
                 color='steelblue', alpha=0.45, label='SPY Drawdown')
ax2.axhline(-10, color='darkred', linestyle='--', linewidth=1.2,
            label='-10% threshold')
shade_regimes(ax2, regimes)
ax2.set_ylabel('Drawdown (%)', fontsize=11)
ax2.set_title('SPY Rolling Drawdown with BAA-GS10 Spread Regime Signal', fontsize=13)
ax2.legend(loc='lower left', fontsize=9)

fig.autofmt_xdate()
fig.tight_layout()
fig.savefig('figures/regime_validation.png', dpi=150, bbox_inches='tight')
plt.show()
print('Figure saved to figures/regime_validation.png')
```

- [ ] **Step 3: Clear all cell outputs** (so the committed notebook is clean)

Use `nbconvert` to strip outputs:

```bash
jupyter nbconvert --to notebook --ClearOutputPreprocessor.enabled=True \
  --output notebooks/01_regime_validation.ipynb \
  notebooks/01_regime_validation.ipynb
```

Or edit the `.ipynb` JSON directly — set `"outputs": []` and `"execution_count": null` on every code cell.

- [ ] **Step 4: Commit**

```bash
git add notebooks/01_regime_validation.ipynb
git commit -m "feat(notebook): update regime validation to use BAA-GS10 composite spread"
```

---

## Self-Review

**Spec coverage:**

| Requirement | Covered by |
|---|---|
| Add `fetch_composite_spread()` to fred_client.py | Task 1 |
| Fetches BAA and GS10, aligns by date, computes BAA − GS10 | Task 1 Step 3 |
| Returns named pd.Series | Task 1 Step 3 + test |
| Update `get_regime_signal()` to use composite | Task 2 Step 3 |
| Update `get_regime_series()` to use composite | Task 2 Step 3 |
| Remove `_SERIES_ID` hardcoded reference | Task 2 Step 3 |
| Add module-level comment explaining substitution | Task 2 Step 3 |
| RED > 3.50, YELLOW 2.50–3.50, GREEN < 2.50 | Already correct in monitor.py; Task 2 Step 3 preserves them |
| Mock both BAA and GS10 fetch calls in tests | Task 1 Step 1 (fred_client tests) and Task 2 Step 1 (monitor tests mock composite) |
| Notebook: fetch BAA and GS10 instead of BAA10Y | Task 3 Step 1 |
| Notebook: compute composite spread | Task 3 Step 1 |
| Notebook: update chart labels | Task 3 Step 2 |
| No other logic changed | Confirmed — SPY fetch, drawdown, event table, pass/fail cells untouched |

**Placeholder scan:** No TBDs or "similar to above" references. All steps include complete code.

**Type consistency:** `fetch_composite_spread(start, end) -> pd.Series` defined in Task 1, called identically in Task 2 (`client.fetch_composite_spread()` and `client.fetch_composite_spread(start=fetch_start, end=end)`). Mock in Task 2 uses `client.fetch_composite_spread.return_value` matching the same signature.
