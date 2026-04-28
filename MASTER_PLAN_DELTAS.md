# Master Plan Deltas

Deviations from `master_plan_v4.md` are recorded here. Each entry explains what
changed, why, and what was preserved from the original intent.

---

## Delta 001 — Regime series: BAMLH0A0HYM2 → BAA10Y

**Date:** 2026-04-28
**Affected files:** `src/regime/monitor.py`, `tests/regime/test_monitor.py`,
`notebooks/01_regime_validation.ipynb`

### What changed

| Item | master_plan_v4 | Actual implementation |
|---|---|---|
| FRED series | `BAMLH0A0HYM2` (ICE BofA US HY OAS) | `BAA10Y` (Moody's Baa–10Y Treasury spread) |
| RED threshold | > 5.50 % | > 3.50 % |
| YELLOW range | 4.00–5.50 % | 2.50–3.50 % |
| GREEN threshold | < 4.00 % | < 2.50 % |

### Why

`BAMLH0A0HYM2` was restricted to a 3-year rolling window on the FRED public API
in April 2026. The full historical series (required for Phase 1 validation back to
2007) is no longer freely accessible. This breaks the notebook validation and
`get_regime_series` for any `start` before the rolling window.

`BAA10Y` (Moody's Seasoned Baa Corporate Bond Yield Relative to Yield on 10-Year
Treasury) is a comparable credit-stress indicator that remains fully open on FRED
with data back to 1986. It is not an OAS series, but it measures the same economic
signal: widening credit spreads indicate rising systemic risk.

### What is preserved

- The three-regime logic (GREEN / YELLOW / RED) and its economic interpretation
  are unchanged.
- The decision rule ("halt new entries at YELLOW; exit all at RED") is unchanged.
- The Phase 1 pass criteria structure is unchanged; only the numeric thresholds
  are recalibrated to the BAA10Y scale.

### Thresholds rationale

BAA10Y historical ranges (approximate):
- Normal / recovery: 0.8–2.0 %  → GREEN (< 2.50)
- Elevated / cautious: 2.0–3.5 %  → YELLOW (2.50–3.50)
- Crisis / stress: > 3.5 %  → RED (GFC peaked ~6 %; COVID peaked ~4 %)

The 3.50 RED threshold is calibrated so that GFC (late 2008 – early 2009) and
COVID (March 2020) both trigger RED. The 2.50 YELLOW threshold captures the
2015–2016 oil-patch stress and 2018 Q4 sell-off as cautionary periods.

### Revalidation required

Phase 1 pass criteria must be re-verified against BAA10Y data using
`notebooks/01_regime_validation.ipynb` before proceeding to Phase 2.
