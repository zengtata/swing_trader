# Systematic Swing Trading System — Master Plan v4

**Reviewer:** Quant Developer perspective
**Document type:** Critique + corrected master plan
**Audience:** Solo developer, limited capital, building from scratch

---

## Part 1 — Critique of Your v3 Plan

Your v3 plan is significantly better than most retail systems. The fact that you already corrected the prior-close limit order, switched to percentile ranking, and deferred paid data until Phase 7 puts you ahead of ~90% of self-built systems. The signal selection (PEAD + revisions + insider) is academically defensible, and the risk framework (HY spread regime, ATR sizing, time-based exit) is sound.

But there are **material flaws** that will either break the system in production or invalidate the backtest. I'll group them by severity.

### 🔴 Critical flaws (will break the system)

#### 1. Alpaca's free data feed cannot compute the VWAP your strategy requires

This is the most important finding. Your VWAP entry logic assumes you can pull "1-minute bars from 9:30 AM" at 10:00 AM and get a real intraday VWAP. **You cannot, on Alpaca's free tier.**

Alpaca's free plan provides only the **IEX feed** for real-time data, or **15-minute delayed SIP**. IEX is a single exchange that captures roughly 2–3% of total US equity volume on a typical day. Your "VWAP" computed from IEX-only bars is not the institutional VWAP that the rest of the market is trading against — it's a sliver-of-a-sliver number that can diverge meaningfully from the real consolidated VWAP, especially on small-mid caps ($200M–$3B) where IEX's share is even thinner.

The 15-minute delayed SIP feed is full-market but useless for intraday execution — by the time you "see" VWAP at 10:00 AM, it's actually 9:45 AM data.

**Implication:** Your strategy as written quietly degrades in live trading because the entry signal is computed against a price series that no major participant is actually seeing. Backtests using Polygon or full SIP data won't match live IEX-based execution.

**Fix options (ranked):**
- **Best:** Use Polygon.io Starter ($29/month, full SIP) from Phase 6 onward. Acknowledge this means Phase 6 is no longer free.
- **Acceptable:** Use **opening range pullback** instead of true VWAP. Mark the high of the first 30 minutes, place a limit at (open + 30-min low) / 2, or at the 10:00 AM low. This is computable from IEX or even 15-min delayed SIP and avoids the false-precision trap.
- **Last resort:** Pay Alpaca's full SIP fee (currently ~$99/month — much higher than the $29 you budgeted).

#### 2. yfinance earnings data is unreliable for backtesting

Your Phase 2 deliverable is `compute_sue(ticker, earnings_date)` using `yfinance.ticker.earnings_history`. Three problems:

- **`yfinance` is an unofficial scraper** of Yahoo's frontend. It breaks without warning when Yahoo redesigns pages. There have been multiple multi-week outages in the last 24 months.
- **Earnings estimate history is incomplete and frequently revised post-hoc.** The "consensus estimate" Yahoo shows today for Q3 2019 is often the *current* consensus snapshot, not what the consensus was the day before earnings. This is point-in-time contamination — your SUE calculation uses information that wasn't available at the time.
- **Bankrupt tickers vanish from Yahoo entirely.** A backtest using yfinance for the universe will silently drop every company that delisted, which is the textbook definition of survivorship bias your plan claims to avoid.

**Implication:** Your "free" Phase 2 data is fundamentally compromised. You can build the engine with yfinance, but you cannot trust the backtest results.

**Fix:** For the backtest specifically, use SEC EDGAR 8-K filings (free) to extract actual EPS at the time of announcement, and use the **Wharton Research Data Services I/B/E/S Academic** access if you have any university affiliation. Otherwise, accept that the "free" backtest is directional only and the real validation happens in paper trading. Budget for **Sharadar SF1 ($60/month, point-in-time clean) or the Polygon fundamentals endpoint** as a Phase 5 cost, not Phase 7.

#### 3. The universe ($200M–$3B) doesn't match the data sources

Mid/small caps are where PEAD edge is largest (less analyst coverage = slower price discovery). But this is also where:
- yfinance data quality is worst
- IEX share of volume is lowest (often <1%)
- Bid-ask spreads are widest (your 10 bps transaction cost assumption is optimistic — 25–50 bps is more realistic for $300M-cap stocks)
- Insider buying volume thresholds need to scale (your $50,000 floor is reasonable for $1B+ caps, too high for $200M caps where a $30k insider buy can be meaningful)

**Implication:** Your universe choice maximizes alpha potential but also maximizes data quality and execution friction. The plan does not budget for this.

**Fix:** Either (a) raise the floor to $1B–$10B and accept lower expected alpha but more reliable execution, or (b) keep the universe but budget realistic transaction costs (30 bps round-trip minimum) in the backtest, and require Sharpe > 1.3 (not 1.0) before going live to leave room for live-vs-backtest slippage.

### 🟠 Significant flaws (will hurt performance materially)

#### 4. Signal weights are asserted, not derived

You've fixed `0.50 * sue + 0.35 * revision + 0.15 * insider`. Where do these numbers come from? They appear to be intuition. In production quant work, weights are either:
- **Equal-weighted** (the honest default — implies "I don't know which signal is better")
- **Inverse-volatility weighted** (each signal contributes equal risk)
- **Fitted on training data** (with strict out-of-sample validation, which adds overfitting risk)

The danger of asserted weights is that they encode bias from a single backtest where you tweaked them until results looked good — that's curve-fitting wearing a suit.

**Fix:** Start with equal weights (0.33 each). Run the backtest. Compare to inverse-vol weights. Only deviate from these if you have a clear, ex-ante reason (e.g., "PEAD has 40 years of academic literature, revisions has 25 years, insider has 15 — therefore I will tilt toward PEAD"). Document the reason *before* you see the results.

#### 5. The 10-candidate top-N selection is a hidden cliff

`universe_df.nlargest(10, 'alpha_score')` always returns 10 names, regardless of how strong the signal is. In a weak earnings season, your #10 candidate might have an alpha score of 0.55 — barely above median. You will trade it anyway because the rule says "top 10."

**Fix:** Add an **absolute threshold** alongside the relative ranking. Something like:

```python
candidates = universe_df[universe_df['alpha_score'] > 0.70].nlargest(10, 'alpha_score')
```

This means: take up to 10 candidates, but only those scoring in the top 30% of the universe. Some weeks you'll have zero trades. That's correct behavior — not a bug.

#### 6. The 8-quarter SUE denominator is unstable for many stocks

`sue = surprise / historical_surprises.std()` with 8 observations means you're estimating a standard deviation from 8 data points. For stocks with consistent beats (every quarter +0.02), the std is near zero, so SUE explodes to infinity for any non-trivial surprise. For stocks with one-time outliers (acquisitions, restructurings), std is huge and SUE is near zero.

**Fix:** Use a **robust scale estimator** — median absolute deviation (MAD) instead of std, or pool the denominator across all stocks in the same sector/size bucket rather than estimating it per-stock from 8 observations.

#### 7. ATR-based stops without considering gap risk

You place a GTC stop at entry + 2.5 ATR below. This works great in normal markets. It fails catastrophically when a stock gaps down 15% on bad guidance overnight — your stop fills at the next-morning print, well below the stop price. On a $300M-cap stock the gap-through can be 3–5x your intended stop loss.

**Fix:** Either (a) explicitly model gap risk in the backtest by replacing stop-fill with the *open* price when the stock gaps below the stop, or (b) cap position sizing at the 99th-percentile historical gap-down for the universe. Don't pretend the stop guarantees your max loss.

### 🟡 Process / methodology flaws

#### 8. The build sequence has no walk-forward validation

Your Phase 5 is "backtest 2015–2022, hold out 2023–2024." Single train/test split is a 1990s-era methodology. Modern practice is **walk-forward** or **expanding-window** validation: train on 2015–2018, test 2019; train on 2015–2019, test 2020; etc. This catches regime-dependent overfitting that a single split misses (e.g., your model works great in low-vol periods but blows up in 2020 — single split can hide this).

**Fix:** Add walk-forward as Phase 5b. It's not optional for a system you intend to live-trade.

#### 9. No "system off" criteria

You have entry rules, exit rules, regime rules. You don't have a clear rule for **"the system itself is broken, stop trading entirely."** Live trading systems silently degrade — the math still runs, the orders still fire, but the edge is gone. Without explicit kill criteria, you'll keep trading a dead system for months.

**Fix:** Define hard kill criteria upfront, such as:
- Live Sharpe < 0 over any rolling 6-month window → halt and review
- 6 consecutive months where live results are >1 standard deviation worse than backtest → halt
- Any single-day loss > 3x backtest's worst day → halt
- Drawdown exceeds 1.5x backtest's worst drawdown → halt

#### 10. Capital sizing is missing from Phase 7

"Starting capital $5,000–$10,000." On a $5,000 account with 8 max positions at 1% risk and $200M–$3B universe stocks averaging $40/share, you'll often get fractional-share positions or 1–2 share positions. Commissions are zero on Alpaca but **slippage and minimum-tick effects are not** — a 1-share order on a $300M-cap stock with a $0.05 spread costs you 0.1%+ on entry alone.

**Realistic minimum:** $25,000 to deploy this system as designed. Below that, you're paying disproportionate friction and your live results will not match the backtest.

### 🟢 Minor / cosmetic

- **Insider blackout window is 2–4 weeks before earnings**, not 30–45 days. Your card overstates this slightly. Doesn't affect the model but worth correcting.
- **`fred.get_series('BAMLH0A0HYM2').iloc[-1]`** can return NaN on bank holidays. Add a `.dropna()` before `.iloc[-1]`.
- **Day +1 entry "never day 0"** is correct, but you should also exclude **day -1** (companies sometimes pre-announce). Use a 2-day quiet window before earnings.
- **"Mean ~0, right tail"** for SUE distribution — this is wrong. SUE should be roughly symmetric around zero in a representative universe; the right tail being heavier than the left would itself be an exploitable signal worth investigating, not an expected default.

---

## Part 2 — Master Plan v4 (Corrected)

### Strategic principles

1. **Prove the math before spending money.** Free tools through end of Phase 4. Targeted spend in Phase 5+.
2. **Every assumption is a potential failure mode.** Each phase ends with a written validation check, not a vibe.
3. **Out-of-sample data is sacred.** 2024–2025 is held out and never touched until Phase 7.
4. **Live trading is paid education.** First $5,000 of P&L variance is tuition, not signal.
5. **The system is a falsifiable hypothesis.** Define kill criteria upfront so you can recognize when it's dead.

### System parameters (revised)

| Parameter | v3 value | v4 value | Rationale |
|---|---|---|---|
| Universe market cap | $200M–$3B | $1B–$10B | Better data quality, tighter spreads, still inefficient enough for PEAD edge |
| Hold period | 3–15 days | 5–15 days | Avoids the noise of days 1–4 post-earnings |
| Signal weights | 0.50/0.35/0.15 | 0.33/0.33/0.33 (start), revisit after backtest | Equal weighting is the honest prior |
| SUE denominator | per-stock std, 8 quarters | per-sector MAD, 8 quarters pooled | Robust to outliers and small samples |
| Stop loss | 2.5× ATR fixed | 2.5× ATR + gap-risk adjustment | Models actual fill price on gaps |
| Top-N selection | top 10 always | top 10, only if alpha_score > 0.70 | Avoids forced trading in weak weeks |
| Insider blackout | 30–45 days | 2–4 weeks (corrected fact) | Matches actual SEC norms |
| Backtest costs | 10 bps/trade | 25 bps/trade round-trip | Realistic for chosen universe |
| Sharpe threshold | > 1.0 | > 1.3 | Buffer for live slippage |
| Validation method | single split | walk-forward + final OOS | Standard practice |

### Build sequence (revised)

#### Phase 0 — Pre-flight (week 0, free, ~3 days)

Before any code: write a one-page **investment thesis** that states, in plain English, why you believe each of the three signals captures real alpha, citing at least one academic paper per signal. If you cannot articulate this, you don't yet understand the system enough to build it.

**Suggested papers:** Bernard & Thomas (1989) for PEAD, Womack (1996) for analyst revisions, Lakonishok & Lee (2001) for insider buying.

**Deliverable:** `thesis.md` — one page, three signals, three citations, three sentences each on the economic mechanism.

**Pass criteria:** Any reasonably skeptical person reading it would say "okay, this isn't crazy."

#### Phase 1 — Regime monitor (weeks 1–2, free, Jupyter)

Build `get_regime_signal()` from FRED's `BAMLH0A0HYM2`. Validate against 2008, 2011, 2015, 2018, 2020, 2022. Plot signal vs. SPY drawdown.

**Deliverable:** `regime.py` with `get_regime_signal() -> Literal["GREEN", "YELLOW", "RED"]`.

**Pass criteria:** RED at least 5 trading days before SPY drawdown crosses 10% in 2008-09 and 2020. Flag YELLOW or RED in 2022 H1.

**Watch out for:** NaN values on bank holidays. Don't use `iloc[-1]` blindly.

#### Phase 2 — Universe construction (weeks 3–4, free + ~$5 one-time, Jupyter)

Build a survivorship-bias-free universe. **Do not** use yfinance for the constituent list. Use either:
- The Wikipedia historical S&P 500 constituent change list (free, requires careful parsing)
- The fja05680/sp500 GitHub project (free, well-maintained list of constituent changes)

For each historical date, the universe is "stocks in S&P 500 at that date with market cap in $1B–$10B." Store as a parquet file indexed by date.

**Deliverable:** `universe.parquet` with columns `date, ticker, market_cap_usd`.

**Pass criteria:** Lehman Brothers appears in the universe in 2007 and disappears in September 2008. (If it doesn't, your universe has survivorship bias.)

**Watch out for:** Tickers that change names (FB → META, GOOG/GOOGL splits, etc.). The fja05680 list handles most but not all.

#### Phase 3 — SUE engine (weeks 5–6, free, Jupyter)

Pull earnings actuals and estimates. Use **SEC EDGAR 8-K filings** for actuals (point-in-time correct) and **yfinance recommendations** for estimates (acknowledged-imperfect, will replace in Phase 5). Compute SUE using sector-pooled MAD as the denominator.

**Deliverable:** `compute_sue(ticker, earnings_date, sector_mad_table) -> float`.

**Pass criteria:**
- SUE distribution across 2018–2022 is roughly symmetric, mean near 0, std around 1.0
- Adding a synthetic SUE of 100 to the universe does not distort other rankings (validates the percentile-rank step downstream)
- Top-decile SUE stocks outperform bottom-decile by at least 50 bps on day +1 (this is sanity-check evidence the signal exists at all in your data)

**Watch out for:** `filing_date` vs. `period_end_date`. Always use filing_date for point-in-time integrity. yfinance estimate data is ~70% reliable — flag stocks where coverage is missing rather than dropping silently.

#### Phase 4 — Multi-signal composite (weeks 7–8, free, Jupyter)

Add the analyst revision signal (yfinance recommendations + a 10-day window) and the insider signal (SEC EDGAR Form 4, 180-day lookback, $50k minimum, exclude 10b5-1). Combine via percentile rank with **equal weights initially** (0.33 each).

**Deliverable:** `master_alpha_score(universe_df, as_of_date) -> ranked_df`.

**Pass criteria:**
- Top-decile composite stocks outperform bottom-decile by at least 75 bps over a 5–15 day hold period
- The top-N selection includes the absolute threshold (`alpha_score > 0.70`)
- Outlier robustness: inject a synthetic SUE = 100 and confirm rankings are stable

**Watch out for:** `as_of_date` discipline. Every input must be filtered to data available *before* `as_of_date`. One leak here invalidates everything downstream.

#### Phase 5 — Backtest infrastructure + paid data upgrade (weeks 9–14, ~$60/month, Jupyter)

This is where the plan diverges from yours. **Spend money here, not at Phase 7.** A backtest on contaminated data is worse than no backtest — it gives false confidence.

**Subscribe to:**
- **Sharadar SF1** ($60/month) for point-in-time fundamentals and clean earnings actuals/estimates, OR
- **Polygon.io Starter** ($29/month) plus a one-time historical earnings dataset purchase

Rebuild the SUE engine using clean data. Re-run Phase 4 outputs. Compare to Phase 4 results — if they diverge significantly, the yfinance-based result was the lie.

Run **walk-forward validation** on 2015–2023, holding 2024–2025 out:
- Train: 2015–2017 → Test: 2018
- Train: 2015–2018 → Test: 2019
- Train: 2015–2019 → Test: 2020
- ... and so on through 2023

**Deliverable:** `backtest_results.parquet` with per-trade metrics, equity curve, and walk-forward Sharpe by year.

**Pass criteria:**
- Walk-forward Sharpe > 1.3 in at least 5 of 6 test years, after 25 bps round-trip costs
- Max drawdown < 25% in worst year
- No single year's Sharpe is > 2× the median (suggests luck, not edge)
- Win rate 45–55% — if higher, you're probably overfitting

**Watch out for:** The temptation to tune parameters until walk-forward looks good. That's still in-sample tuning — it's just spread across more samples. Tune at most twice.

#### Phase 6 — Paper trading with real-time execution (weeks 15–22, ~$60/month + execution data, Alpaca paper)

**Critical decision point on execution:**

You have three choices for entry execution. Pick one and commit:

**A) Opening-range pullback (FREE, recommended for solo retail):**
- 9:30–10:00 AM: stand aside
- At 10:00 AM: mark the high and low of the first 30 minutes
- Place limit at: `(open_price + first_30min_low) / 2`
- Cancel at 10:30 AM if not filled

This is computable from IEX data alone (you only need OHLC, not full volume) and approximates what a VWAP entry is trying to do. Ugly but honest.

**B) True VWAP entry with Polygon Starter ($29/month for Phase 6+):**
- The plan as you wrote it, but with full-SIP minute bars from Polygon

**C) Alpaca AlgoTrader Plus / Unlimited (~$99/month):**
- Real-time SIP via Alpaca, simplifies the stack at higher cost

Choose A or B. C makes no economic sense at your capital level.

**Run paper trading for 60 calendar days** — not "60 trading days," not "until results look good," not "until I get bored." Sixty calendar days, then evaluate.

**Deliverable:** Fully automated daily pipeline running on a cheap VPS or Raspberry Pi.

**Pass criteria:**
- Paper Sharpe over the 60-day window is within ±0.5 of backtest expectation for that period
- All system failures (API outages, halted stocks, partial fills, earnings date shifts) are caught and handled — no silent skipping
- You did not modify the strategy mid-window

**Watch out for:** The strong urge to "fix things you noticed." Write them down. Implement them after the 60 days. Mid-window changes invalidate the whole evaluation.

#### Phase 7 — Live deployment (week 23+, ~$60/month, real capital)

Only after Phase 6 passes. Then and only then, run the held-out 2024–2025 walk-forward as your final validation.

**Capital deployment ladder:**
- Months 1–2: $5,000 (or 10% of intended size — whichever is greater)
- Months 3–6: $15,000 if month-1 metrics are within ±0.5 Sharpe of backtest
- Months 7+: scale to target if 6-month Sharpe is within ±0.3 of backtest

**Kill criteria (hard rules, written in advance):**
1. Live Sharpe < 0 over any rolling 6-month window → halt, review, do not restart without finding the regression
2. Any 30-day window where live performance is > 2 standard deviations worse than backtest expectation → halt
3. Single-day loss > 3× backtest's worst day → halt, investigate immediately
4. Drawdown exceeds 1.5× backtest's worst drawdown → halt, do not restart at full size
5. Three of the above kills in any 12-month period → retire the system; the alpha is gone or never existed

**Watch out for:** Sunk-cost reasoning. After 6 months of work and $400 in data, every signal that the system is broken will feel like noise. The kill criteria exist precisely because they will feel wrong when triggered.

### Total budget summary

| Phase | Duration | Monthly cost | Cumulative |
|---|---|---|---|
| 0 | 3 days | $0 | $0 |
| 1 | 2 weeks | $0 | $0 |
| 2 | 2 weeks | ~$5 (one-time, optional) | $5 |
| 3 | 2 weeks | $0 | $5 |
| 4 | 2 weeks | $0 | $5 |
| 5 | 6 weeks | $60/month for ~2 months = $120 | $125 |
| 6 | 8 weeks | $60–90/month for 2 months = $180 | $305 |
| 7 | ongoing | $60–90/month | + $60–90/month indefinitely |

**Time to first live trade:** ~22 weeks (vs. your 19 weeks). The extra 3 weeks buys you walk-forward validation and clean data — both non-negotiable for a real system.

**Total spend before live capital:** ~$305 over 22 weeks. If $300 feels like too much to spend before risking real money, the system is not yet for you — and that's a perfectly defensible answer.

### What this plan does not include (and why)

- **Machine learning.** You don't have enough data, and the three signals you're combining are well-understood. ML adds variance without adding signal at this scale.
- **Options overlay.** Adds complexity and theta decay. Reconsider after 12 months of clean live equity returns.
- **Crypto / FX / futures.** Different microstructure. Build one system end-to-end before branching.
- **Sentiment / news / Reddit data.** Mostly noise at swing-trade horizons. Reconsider only if your three core signals consistently fail.
- **High-frequency anything.** Wrong horizon, wrong infrastructure, wrong economic logic for your capital level.

### One-page summary for the wall

> The system trades the post-earnings-announcement drift in $1B–$10B US equities, entering on a pullback after 10:00 AM, sized so that hitting a 2.5× ATR stop costs 1% of capital, exited unconditionally on day 15. Three signals (SUE, revisions, insider buying) are equal-weighted via percentile rank and combined into a daily ranking; trades are taken only on names scoring above the 70th percentile. The system halts entirely when high-yield credit spreads exceed 5.5%. It is built free through Phase 4, costs ~$60–90/month from Phase 5 onward, and is retired if any of five hard kill criteria are triggered.

That's the system. Everything else is implementation detail.

---

## Final word

The single biggest mistake retail quants make isn't bad signals — it's claiming victory too early. Your v3 plan was already past the worst pitfalls. v4 closes the remaining gaps: clean data, walk-forward validation, realistic execution, and pre-committed kill criteria.

Build this in the order written. Skip nothing. Most of the work is in Phases 2, 5, and 6 — the unglamorous parts. The three "interesting" phases (1, 3, 4) are the easy ones. Your edge, if it exists, is not in the signals — those are widely known. Your edge is in the discipline of the build.
