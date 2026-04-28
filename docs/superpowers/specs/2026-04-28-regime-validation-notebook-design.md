# Regime Validation Notebook — Design Spec
**Date:** 2026-04-28
**Phase:** Master Plan v4 — Phase 1 validation deliverable

---

## Goal

Produce `notebooks/01_regime_validation.ipynb` that proves (or disproves) the HY OAS regime
classifier meets the Phase 1 pass criteria from `master_plan_v4.md`.

---

## Dependencies

Add to project via `uv add`:
- `yfinance` — SPY daily closes only; acceptable for index-level validation
- `matplotlib` — static plot output

---

## Data sources

| Data | Source | Why |
|---|---|---|
| HY OAS regime series (2007-01-01 → 2024-12-31) | `get_regime_series()` from `src.regime.monitor` | Uses FREDClient; no bypass |
| SPY daily closes (same period) | `yf.download("SPY", auto_adjust=True)["Close"]` | Index-level only, noted limitation |

---

## Notebook structure (7 cells)

### Cell 1 — Setup
Imports, `load_dotenv()`, `matplotlib` config, create `notebooks/figures/` if absent.

### Cell 2 — Fetch regime series
```python
regimes = get_regime_series(date(2007, 1, 1), date(2024, 12, 31))
```
No bypass. This calls the real FRED API.

### Cell 3 — Fetch SPY and compute drawdown
```python
spy = yf.download("SPY", start="2007-01-01", end="2024-12-31", auto_adjust=True)["Close"].squeeze()
drawdown = (spy / spy.cummax() - 1) * 100   # negative percentages
```

### Cell 4 — Plot
Two stacked subplots sharing x-axis.
- **Top:** SPY price line, background shaded by regime (green/gold/red, alpha=0.2)
- **Bottom:** SPY drawdown (%), background shaded by regime identically
- Figure saved to `notebooks/figures/regime_validation.png`

Regime shading: iterate over contiguous regime blocks; call `ax.axvspan(start, end, color=..., alpha=0.2)`.

### Cell 5 — Validation table
For each event:

| Event | Scan start | Description |
|---|---|---|
| 2008-09 GFC | 2007-01-01 | Rising spreads pre-Lehman captured |
| 2020-02/03 COVID | 2020-01-01 | No pre-signal expected; tests speed |
| 2022 H1 Fed tightening | 2021-01-01 | YELLOW or RED trigger, not necessarily RED |

Per event: find first date regime hit RED (or YELLOW for 2022), find first date drawdown crossed
-10%, compute lead time via `np.busday_count`.

Output: pandas DataFrame with columns `event`, `regime_trigger_date`,
`trigger_level`, `drawdown_10pct_date`, `lead_days`.

### Cell 6 — Pass/Fail evaluation (Markdown)
Evaluate master_plan_v4 pass criteria **as written**:
- PASS GFC: `lead_days(GFC) >= 5`
- PASS COVID: `lead_days(COVID) >= 5`
- PASS 2022: YELLOW or RED present at any point in 2022 H1

If any criterion fails: report **FAIL** clearly. **Do not adjust thresholds.** Thresholds are locked in
`master_plan_v4.md`.

---

## Constraints

- Never bypass `FREDClient` / `get_regime_series`.
- No threshold changes on failure — report and stop.
- Notebook is validation only; no parameter tuning inside it.
