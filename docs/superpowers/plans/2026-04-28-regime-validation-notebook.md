# Regime Validation Notebook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `notebooks/01_regime_validation.ipynb` that validates the HY OAS regime classifier against historical SPY drawdowns and emits a PASS/FAIL verdict against the Phase 1 criteria in `master_plan_v4.md`.

**Architecture:** Single notebook with 7 cells (setup → regime fetch → SPY fetch → plot → validation table → pass/fail); the only new Python logic is inside the notebook cells themselves, with no new `src/` modules. The notebook calls `get_regime_series()` via the real FRED client and fetches SPY via `yfinance`. The figure is saved to `notebooks/figures/regime_validation.png`.

**Tech Stack:** Python 3.11, Jupyter notebook (`.ipynb` JSON), `yfinance`, `matplotlib`, `pandas`, `numpy`, `fredapi` (via existing `FREDClient`).

---

## File Map

| Action | Path | Purpose |
|---|---|---|
| Modify | `pyproject.toml` | Add `yfinance`, `matplotlib` to runtime deps |
| Auto-updated | `uv.lock` | Lock file update from `uv add` |
| Create | `notebooks/figures/.gitkeep` | Ensure figures dir is tracked |
| **Create** | `notebooks/01_regime_validation.ipynb` | The validation notebook |

---

## Task 1 — Add yfinance and matplotlib dependencies

**Files:**
- Modify: `pyproject.toml` (via `uv add`)
- Auto-updated: `uv.lock`

- [ ] **Step 1: Add runtime dependencies**

```bash
uv add yfinance matplotlib
```

Expected output includes lines like:
```
Resolved N packages in ...
Installed yfinance-...
Installed matplotlib-...
```

- [ ] **Step 2: Verify both packages import cleanly**

```bash
python -c "import yfinance; import matplotlib; print('OK')"
```

Expected output: `OK`

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "deps: add yfinance and matplotlib for regime validation notebook"
```

---

## Task 2 — Create the notebook skeleton (setup cell)

**Files:**
- Create: `notebooks/01_regime_validation.ipynb`
- Create: `notebooks/figures/.gitkeep`

- [ ] **Step 1: Create the figures directory placeholder**

```bash
mkdir -p notebooks/figures
touch notebooks/figures/.gitkeep
```

- [ ] **Step 2: Write the notebook file**

Create `notebooks/01_regime_validation.ipynb` with the following exact JSON:

```json
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Regime Monitor Validation — Phase 1\n",
    "\n",
    "Validates `get_regime_signal()` against historical SPY drawdowns per `master_plan_v4.md` Phase 1 pass criteria.\n",
    "\n",
    "**Pass criteria (from master plan):**\n",
    "- RED ≥ 5 trading days before SPY drawdown crosses −10% in 2008–09 (GFC)\n",
    "- RED ≥ 5 trading days before SPY drawdown crosses −10% in 2020 (COVID)\n",
    "- YELLOW or RED present at any point in 2022 H1 (Fed tightening)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "import sys\n",
    "from pathlib import Path\n",
    "from datetime import date\n",
    "\n",
    "import matplotlib.pyplot as plt\n",
    "import matplotlib.patches as mpatches\n",
    "import numpy as np\n",
    "import pandas as pd\n",
    "import yfinance as yf\n",
    "from dotenv import load_dotenv\n",
    "\n",
    "# Make src/ importable from notebooks/\n",
    "sys.path.insert(0, str(Path('..').resolve()))\n",
    "load_dotenv(Path('../.env'))\n",
    "\n",
    "from src.regime.monitor import get_regime_series\n",
    "\n",
    "Path('figures').mkdir(exist_ok=True)\n",
    "print('Setup complete')"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "name": "python",
   "version": "3.11.0"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
```

- [ ] **Step 3: Commit**

```bash
git add notebooks/01_regime_validation.ipynb notebooks/figures/.gitkeep
git commit -m "notebook: add regime validation skeleton (setup cell)"
```

---

## Task 3 — Add regime series cell

**Files:**
- Modify: `notebooks/01_regime_validation.ipynb` (append cell)

- [ ] **Step 1: Insert the regime fetch cell**

Append the following cell to the `cells` array in the notebook JSON (before the closing `]` of `"cells"`):

```json
{
 "cell_type": "code",
 "execution_count": null,
 "metadata": {},
 "outputs": [],
 "source": [
  "START = date(2007, 1, 1)\n",
  "END   = date(2024, 12, 31)\n",
  "\n",
  "print('Fetching HY OAS regime series from FRED...')\n",
  "regimes = get_regime_series(start=START, end=END)\n",
  "print(f'Regime series: {len(regimes):,} business days ({START} → {END})')\n",
  "print(regimes.value_counts().to_string())"
 ]
}
```

- [ ] **Step 2: Commit**

```bash
git add notebooks/01_regime_validation.ipynb
git commit -m "notebook: add regime series fetch cell"
```

---

## Task 4 — Add SPY fetch and drawdown cell

**Files:**
- Modify: `notebooks/01_regime_validation.ipynb` (append cell)

- [ ] **Step 1: Insert the SPY + drawdown cell**

Append to `"cells"`:

```json
{
 "cell_type": "code",
 "execution_count": null,
 "metadata": {},
 "outputs": [],
 "source": [
  "print('Fetching SPY daily closes from yfinance...')\n",
  "spy_raw = yf.download(\n",
  "    'SPY',\n",
  "    start='2007-01-01',\n",
  "    end='2025-01-01',   # yfinance end is exclusive; use Jan 1 to capture Dec 31\n",
  "    auto_adjust=True,\n",
  "    progress=False,\n",
  ")\n",
  "# Handle both flat and multi-level column structures across yfinance versions\n",
  "close_col = spy_raw['Close']\n",
  "spy = close_col.iloc[:, 0] if isinstance(close_col, pd.DataFrame) else close_col\n",
  "spy = spy.squeeze().rename('SPY')\n",
  "spy.index = pd.to_datetime(spy.index)\n",
  "spy = spy[spy.index <= pd.Timestamp('2024-12-31')]  # clip to requested range\n",
  "\n",
  "# Align to business-day index used by regimes (forward-fill any missing yfinance days)\n",
  "spy = spy.reindex(regimes.index).ffill()\n",
  "\n",
  "# Rolling peak-to-current drawdown (negative percentages)\n",
  "drawdown = (spy / spy.cummax() - 1) * 100\n",
  "\n",
  "print(f'SPY: {len(spy):,} days aligned')\n",
  "print(f'Worst drawdown in period: {drawdown.min():.1f}%')"
 ]
}
```

- [ ] **Step 2: Commit**

```bash
git add notebooks/01_regime_validation.ipynb
git commit -m "notebook: add SPY fetch and rolling drawdown cell"
```

---

## Task 5 — Add plot cell

**Files:**
- Modify: `notebooks/01_regime_validation.ipynb` (append cell)

- [ ] **Step 1: Insert the plot cell**

Append to `"cells"`:

```json
{
 "cell_type": "code",
 "execution_count": null,
 "metadata": {},
 "outputs": [],
 "source": [
  "REGIME_COLORS = {'GREEN': 'green', 'YELLOW': 'gold', 'RED': 'red'}\n",
  "\n",
  "def shade_regimes(ax, regime_series):\n",
  "    \"\"\"Shade background by contiguous regime blocks.\"\"\"\n",
  "    current = None\n",
  "    block_start = None\n",
  "    for dt, val in regime_series.items():\n",
  "        if val != current:\n",
  "            if current is not None:\n",
  "                ax.axvspan(block_start, dt, alpha=0.2,\n",
  "                           color=REGIME_COLORS[current], lw=0)\n",
  "            current = val\n",
  "            block_start = dt\n",
  "    if current is not None:\n",
  "        ax.axvspan(block_start, regime_series.index[-1], alpha=0.2,\n",
  "                   color=REGIME_COLORS[current], lw=0)\n",
  "\n",
  "fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(18, 10), sharex=True)\n",
  "\n",
  "# --- Top: SPY price ---\n",
  "ax1.plot(spy.index, spy.values, color='black', linewidth=0.7, label='SPY Close')\n",
  "shade_regimes(ax1, regimes)\n",
  "ax1.set_ylabel('SPY Price ($)', fontsize=11)\n",
  "ax1.set_title('SPY Price with HY OAS Regime Signal  (2007–2024)', fontsize=13)\n",
  "ax1.legend(\n",
  "    handles=[\n",
  "        mpatches.Patch(color='green', alpha=0.5, label='GREEN — OAS < 4.00'),\n",
  "        mpatches.Patch(color='gold',  alpha=0.5, label='YELLOW — 4.00 ≤ OAS ≤ 5.50'),\n",
  "        mpatches.Patch(color='red',   alpha=0.5, label='RED — OAS > 5.50'),\n",
  "        plt.Line2D([0], [0], color='black', linewidth=0.7, label='SPY Close'),\n",
  "    ],\n",
  "    loc='upper left', fontsize=9,\n",
  ")\n",
  "\n",
  "# --- Bottom: Drawdown ---\n",
  "ax2.fill_between(drawdown.index, drawdown.values, 0,\n",
  "                 color='steelblue', alpha=0.45, label='SPY Drawdown')\n",
  "ax2.axhline(-10, color='darkred', linestyle='--', linewidth=1.2,\n",
  "            label='−10% threshold')\n",
  "shade_regimes(ax2, regimes)\n",
  "ax2.set_ylabel('Drawdown (%)', fontsize=11)\n",
  "ax2.set_title('SPY Rolling Drawdown with HY OAS Regime Signal', fontsize=13)\n",
  "ax2.legend(loc='lower left', fontsize=9)\n",
  "\n",
  "fig.autofmt_xdate()\n",
  "fig.tight_layout()\n",
  "fig.savefig('figures/regime_validation.png', dpi=150, bbox_inches='tight')\n",
  "plt.show()\n",
  "print('Figure saved → figures/regime_validation.png')"
 ]
}
```

- [ ] **Step 2: Commit**

```bash
git add notebooks/01_regime_validation.ipynb
git commit -m "notebook: add two-panel regime plot cell"
```

---

## Task 6 — Add validation table cell

**Files:**
- Modify: `notebooks/01_regime_validation.ipynb` (append cell)

- [ ] **Step 1: Insert the validation table cell**

Append to `"cells"`:

```json
{
 "cell_type": "code",
 "execution_count": null,
 "metadata": {},
 "outputs": [],
 "source": [
  "events = [\n",
  "    dict(name='2008-09 GFC',\n",
  "         scan_start=pd.Timestamp('2007-01-01'),\n",
  "         scan_end=pd.Timestamp('2009-12-31'),\n",
  "         trigger_level='RED'),\n",
  "    dict(name='2020-02/03 COVID',\n",
  "         scan_start=pd.Timestamp('2019-11-01'),\n",
  "         scan_end=pd.Timestamp('2020-12-31'),\n",
  "         trigger_level='RED'),\n",
  "    dict(name='2022 H1 Fed tightening',\n",
  "         scan_start=pd.Timestamp('2021-01-01'),\n",
  "         scan_end=pd.Timestamp('2022-06-30'),\n",
  "         trigger_level='YELLOW_OR_RED'),\n",
  "]\n",
  "\n",
  "rows = []\n",
  "for ev in events:\n",
  "    w_reg = regimes[(regimes.index >= ev['scan_start']) &\n",
  "                    (regimes.index <= ev['scan_end'])]\n",
  "    w_dd  = drawdown[(drawdown.index >= ev['scan_start']) &\n",
  "                     (drawdown.index <= ev['scan_end'])]\n",
  "\n",
  "    # First regime trigger\n",
  "    if ev['trigger_level'] == 'RED':\n",
  "        trigger_mask = w_reg == 'RED'\n",
  "    else:\n",
  "        trigger_mask = w_reg.isin(['YELLOW', 'RED'])\n",
  "\n",
  "    trigger_dates = w_reg.index[trigger_mask]\n",
  "    regime_trigger = trigger_dates[0] if len(trigger_dates) > 0 else None\n",
  "    trigger_level  = w_reg[regime_trigger] if regime_trigger is not None else 'N/A'\n",
  "\n",
  "    # First date drawdown breaches -10 %\n",
  "    dd_breach = w_dd[w_dd <= -10.0]\n",
  "    dd_date   = dd_breach.index[0] if len(dd_breach) > 0 else None\n",
  "\n",
  "    # Lead time in trading days (positive = regime warned first)\n",
  "    if regime_trigger is not None and dd_date is not None:\n",
  "        lead = int(np.busday_count(\n",
  "            regime_trigger.date(), dd_date.date()\n",
  "        ))\n",
  "    else:\n",
  "        lead = None\n",
  "\n",
  "    rows.append({\n",
  "        'Event':                ev['name'],\n",
  "        'Regime Trigger Date':  regime_trigger.date() if regime_trigger else 'N/A',\n",
  "        'Trigger Level':        trigger_level,\n",
  "        'DD −10% Date':         dd_date.date() if dd_date else 'N/A',\n",
  "        'Lead (trading days)':  lead if lead is not None else 'N/A',\n",
  "    })\n",
  "\n",
  "val_df = pd.DataFrame(rows)\n",
  "print(val_df.to_string(index=False))"
 ]
}
```

- [ ] **Step 2: Commit**

```bash
git add notebooks/01_regime_validation.ipynb
git commit -m "notebook: add validation table cell"
```

---

## Task 7 — Add pass/fail evaluation cell

**Files:**
- Modify: `notebooks/01_regime_validation.ipynb` (append two cells)

The pass/fail cell is a **code cell** that computes verdicts and renders them as formatted Markdown using `IPython.display`.

- [ ] **Step 1: Insert the pass/fail code cell**

Append to `"cells"`:

```json
{
 "cell_type": "code",
 "execution_count": null,
 "metadata": {},
 "outputs": [],
 "source": [
  "from IPython.display import Markdown, display\n",
  "\n",
  "def _row(name):\n",
  "    return val_df[val_df['Event'] == name].iloc[0]\n",
  "\n",
  "gfc   = _row('2008-09 GFC')\n",
  "covid = _row('2020-02/03 COVID')\n",
  "h22   = _row('2022 H1 Fed tightening')\n",
  "\n",
  "# --- evaluate criteria ---\n",
  "def _lead_ok(row, min_days=5):\n",
  "    lead = row['Lead (trading days)']\n",
  "    return isinstance(lead, int) and lead >= min_days\n",
  "\n",
  "def _triggered(row):\n",
  "    return row['Trigger Level'] in ('YELLOW', 'RED')\n",
  "\n",
  "# For 2022 H1 pass: YELLOW or RED must appear *within* 2022 H1 specifically\n",
  "h22_window = regimes[\n",
  "    (regimes.index >= pd.Timestamp('2022-01-01')) &\n",
  "    (regimes.index <= pd.Timestamp('2022-06-30'))\n",
  "]\n",
  "h22_triggered = h22_window.isin(['YELLOW', 'RED']).any()\n",
  "\n",
  "pass_gfc   = _lead_ok(gfc)\n",
  "pass_covid = _lead_ok(covid)\n",
  "pass_2022  = bool(h22_triggered)\n",
  "\n",
  "overall = pass_gfc and pass_covid and pass_2022\n",
  "\n",
  "def _tick(ok): return '✅ PASS' if ok else '❌ FAIL'\n",
  "\n",
  "lines = [\n",
  "    '## Phase 1 Pass/Fail — master_plan_v4.md criteria',\n",
  "    '',\n",
  "    f'| Criterion | Result | Detail |',\n",
  "    f'|---|---|---|',\n",
  "    f'| RED ≥ 5 trading days before −10% drawdown (GFC 2008–09) | {_tick(pass_gfc)} | Lead = {gfc[\"Lead (trading days)\"]} days |',\n",
  "    f'| RED ≥ 5 trading days before −10% drawdown (COVID 2020) | {_tick(pass_covid)} | Lead = {covid[\"Lead (trading days)\"]} days |',\n",
  "    f'| YELLOW or RED in 2022 H1 (Fed tightening) | {_tick(pass_2022)} | Triggered = {h22_triggered} |',\n",
  "    '',\n",
  "    f'### Overall: {\"✅ PASS\" if overall else \"❌ FAIL\"}',\n",
  "]\n",
  "\n",
  "if not overall:\n",
  "    lines += [\n",
  "        '',\n",
  "        '> **FAIL — thresholds are locked in master_plan_v4.md.**',\n",
  "        '> Do not adjust the 4.00 / 5.50 thresholds to force a pass.',\n",
  "        '> Investigate the data quality or the event window definitions instead.',\n",
  "    ]\n",
  "\n",
  "display(Markdown('\\n'.join(lines)))"
 ]
}
```

- [ ] **Step 2: Commit**

```bash
git add notebooks/01_regime_validation.ipynb
git commit -m "notebook: add pass/fail evaluation cell"
```

---

## Task 8 — Smoke-run and final commit

- [ ] **Step 1: Verify the notebook JSON is valid**

```bash
python -c "import json; json.load(open('notebooks/01_regime_validation.ipynb')); print('JSON OK')"
```

Expected: `JSON OK`

- [ ] **Step 2: Run the notebook end-to-end**

Open `notebooks/01_regime_validation.ipynb` in Jupyter and run all cells top-to-bottom (`Kernel → Restart & Run All`). Confirm:
- Cell 2 prints regime value counts
- Cell 3 prints worst drawdown (should be around −56% for GFC)
- Cell 4 saves the figure and shows the plot
- Cell 5 prints the validation table (4 columns, 3 rows)
- Cell 6 renders a Markdown table with PASS or FAIL for each criterion

- [ ] **Step 3: Commit the executed notebook output**

```bash
git add notebooks/01_regime_validation.ipynb notebooks/figures/regime_validation.png
git commit -m "notebook: add executed regime validation results"
```
