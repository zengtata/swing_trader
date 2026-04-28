# Terminal Execution Blueprint — Swing Trading System

**Source of truth:** `master_plan_v4.md` (do not modify — trading logic is locked)
**Execution tool:** Claude Code (Anthropic CLI, run from project root)
**Methodology:** Agile sprints, one ticket = one Claude Code prompt
**Coverage:** Sprint 0 (bootstrap) + Sprints 1–6 (mapping to Phases 1–6)

---

## How to use this document

1. **Open two windows:** your terminal running `claude` in the project root, and this document for reference.
2. **One ticket at a time.** Each ticket has a single, copy-pasteable prompt. Do not bundle prompts. Do not run them out of order.
3. **Verify before moving on.** Each ticket has a `Verify` block — run it. If it fails, debug with Claude Code in the same session before moving to the next ticket.
4. **Use `/clear` between tickets** to keep context fresh. Use `/compact` if a single ticket gets long. Claude Code's `CLAUDE.md` file (created in Ticket 0.1) provides standing context across `/clear` calls.
5. **Commit after every passing ticket.** `git add -A && git commit -m "ticket X.Y"`. This makes failed prompts cheap to roll back.

## Prerequisites (do these BEFORE Sprint 1)

- [ ] Master plan thesis written (`thesis.md`) — non-code, master plan Phase 0
- [ ] Python 3.11+ installed (`python --version`)
- [ ] `uv` installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`) — modern, fast Python package manager
- [ ] Git installed and configured
- [ ] Claude Code installed (`npm install -g @anthropic-ai/claude-code`)
- [ ] FRED API key obtained (free, https://fred.stlouisfed.org/docs/api/api_key.html)
- [ ] SEC EDGAR User-Agent string prepared (format: `"Your Name your.email@example.com"` — required by SEC)

API keys for later sprints (set up just before that sprint, not now):
- Polygon.io Starter — Sprint 5
- Alpaca paper trading — Sprint 6

---

# Sprint 0 — Project Bootstrap

**Sprint goal:** Make the project ready for development. No trading logic written yet.
**Duration:** 1 day
**Definition of done:** `pytest` runs (with zero tests), `ruff` lints clean, `mypy` type-checks clean, `CLAUDE.md` exists at root.

### Ticket 0.1 — Initialize project skeleton + CLAUDE.md

**Goal:** Create the directory tree, `pyproject.toml`, lint/test config, and the standing-instructions file Claude Code reads automatically.
**Deliverable:** Project structure, `CLAUDE.md`, working `uv` environment.

**Prompt:**
```
Initialize a Python 3.11 project in the current directory for a systematic swing trading system. Use `uv` as the package manager (uv init, uv add, uv run).

Create this structure:
  src/
    config/        # config loading, .env handling
    regime/        # Sprint 1
    universe/      # Sprint 2
    signals/       # Sprints 3, 4
    backtest/      # Sprint 5
    execution/     # Sprint 6
    common/        # logging, types, utilities
  tests/
    (mirror of src/)
  notebooks/       # exploratory Jupyter only, not for production code
  data/
    raw/           # API pulls, gitignored
    processed/     # parquet outputs, gitignored
  scripts/         # one-off CLI scripts
  .env.example     # template, committed
  .gitignore
  pyproject.toml
  README.md
  CLAUDE.md

Configure pyproject.toml with these dev dependencies: pytest, pytest-mock, ruff, mypy, ipykernel. Runtime dependencies: pandas, numpy, python-dotenv, pydantic-settings.

Create CLAUDE.md with these standing instructions for any future Claude Code session:
- Source of truth for trading logic is /master_plan_v4.md — never override it
- Use type hints everywhere (Python 3.11 syntax: list[str], dict[str, int], X | None)
- Every public function gets a pytest test in the mirrored tests/ path
- Mock all external APIs in tests — never hit live FRED/EDGAR/Polygon/Alpaca in pytest
- Use pandas with explicit dtypes; never store dates as strings
- Use parquet (not CSV) for any DataFrame written to disk
- Logging via the standard logging module with a logger per module: logger = logging.getLogger(__name__)
- No print() statements outside of CLI scripts
- All API keys come from environment variables loaded via src/config — never hardcode
- When adding a dependency, use `uv add` (not pip install)
- Stay strictly within the scope of the current ticket. Do not refactor unrelated code.
- If a requirement is ambiguous, ask one clarifying question rather than guessing

Add a .gitignore that excludes: .venv/, __pycache__/, .pytest_cache/, .mypy_cache/, *.pyc, .env, data/raw/, data/processed/, .ipynb_checkpoints/, .DS_Store

Add a .env.example with placeholder lines for: FRED_API_KEY, SEC_EDGAR_USER_AGENT, POLYGON_API_KEY, ALPACA_API_KEY, ALPACA_API_SECRET, ALPACA_BASE_URL

Run `uv sync` to create the lockfile. Verify by running `uv run pytest` (should report 0 tests collected, exit 0) and `uv run ruff check .` (should pass).

Do not write any business logic in this ticket. Just the skeleton.
```

**Verify:**
```bash
uv run pytest                # 0 tests, exit code 0
uv run ruff check .          # clean
uv run mypy src              # clean (no source files yet)
test -f CLAUDE.md            # exists
```

### Ticket 0.2 — Config and logging modules

**Goal:** Centralized settings loaded from `.env`, plus a logging setup helper.
**Deliverable:** `src/config/settings.py`, `src/common/logging.py`, tests for both.

**Prompt:**
```
In src/config/settings.py, implement a Pydantic BaseSettings class called Settings that loads these fields from environment variables (via .env using python-dotenv):
  fred_api_key: str
  sec_edgar_user_agent: str
  polygon_api_key: str | None = None      # not required until Sprint 5
  alpaca_api_key: str | None = None       # not required until Sprint 6
  alpaca_api_secret: str | None = None
  alpaca_base_url: str = "https://paper-api.alpaca.markets"

Expose a single function get_settings() that returns a cached Settings instance (use functools.lru_cache).

In src/common/logging.py, implement setup_logging(level: str = "INFO") -> None that configures the root logger with a single StreamHandler, format string "%(asctime)s [%(levelname)s] %(name)s: %(message)s", and ISO-8601 timestamps.

Write tests:
- tests/config/test_settings.py: use pytest's monkeypatch to set env vars, verify Settings loads correctly. Verify that missing fred_api_key raises a ValidationError.
- tests/common/test_logging.py: verify setup_logging adds a handler and sets the right level. Use caplog fixture.

Stay within scope. Do not import or build anything related to FRED, EDGAR, or trading logic in this ticket.
```

**Verify:**
```bash
cp .env.example .env  # then edit .env, fill FRED_API_KEY and SEC_EDGAR_USER_AGENT
uv run pytest tests/config tests/common -v
```

---

# Sprint 1 — Regime Monitor

**Sprint goal:** Build a working `get_regime_signal()` that returns GREEN/YELLOW/RED from FRED data, validated against historical drawdowns.
**Duration:** Master plan estimate: 2 weeks. Claude Code estimate: 1–2 days.
**Definition of done:** Master plan Phase 1 pass criteria met (RED ≥5 trading days before SPY drawdown crosses 10% in 2008-09 and 2020; YELLOW or RED in 2022 H1).

### Ticket 1.1 — FRED client wrapper

**Goal:** Thin wrapper around `fredapi` with caching and error handling. No trading logic yet.
**Deliverable:** `src/regime/fred_client.py`, tests with mocked fredapi.

**Prompt:**
```
In src/regime/fred_client.py, implement a class FREDClient that wraps the fredapi library.

Constructor: FREDClient(api_key: str). Use the api_key from get_settings().fred_api_key by default if a factory function FREDClient.from_settings() is called.

Methods:
  fetch_series(series_id: str, start: date | None = None, end: date | None = None) -> pd.Series
    - Returns a pandas Series indexed by date (datetime64[ns]), float64 values
    - Drops NaN values before returning
    - Raises FREDFetchError (custom exception in same module) on any underlying API failure with the original error chained
  
Add an in-memory cache (functools.lru_cache will not work because pd.Series is unhashable; use a dict keyed by (series_id, start, end) tuple). Cache size: unlimited within a process — these series are small.

Tests in tests/regime/test_fred_client.py:
- Use pytest-mock to patch fredapi.Fred.get_series
- Verify fetch_series drops NaN
- Verify FREDFetchError is raised and chained on underlying exceptions
- Verify the cache returns the same object on second call with same args

Do NOT pull live data in tests.
```

**Verify:**
```bash
uv run pytest tests/regime/test_fred_client.py -v
# Manual smoke test (one-time, real API):
uv run python -c "from src.regime.fred_client import FREDClient; c = FREDClient.from_settings(); print(c.fetch_series('BAMLH0A0HYM2').tail())"
```

### Ticket 1.2 — `get_regime_signal()` function

**Goal:** The core regime classifier. Both real-time (no `as_of`) and historical (with `as_of`) modes.
**Deliverable:** `src/regime/monitor.py`, comprehensive tests.

**Prompt:**
```
In src/regime/monitor.py, implement the regime classifier per master_plan_v4.md Phase 1.

Function signature:
  def get_regime_signal(as_of: date | None = None, client: FREDClient | None = None) -> Literal["GREEN", "YELLOW", "RED"]

Logic:
- Fetch series 'BAMLH0A0HYM2' (ICE BofA US HY OAS) via FREDClient
- Drop NaN values
- If as_of is None: use the most recent value
- If as_of is provided: use the most recent value with index <= as_of (this is the "as known on date" semantics — never look ahead)
- Thresholds (from master_plan v4):
    spread > 5.50 → "RED"
    4.00 <= spread <= 5.50 → "YELLOW"
    spread < 4.00 → "GREEN"
- If client is None, instantiate FREDClient.from_settings()

Add a second function for backtest use:
  def get_regime_series(start: date, end: date, client: FREDClient | None = None) -> pd.Series
    - Returns a pd.Series indexed by date, dtype object (categorical strings)
    - Forward-fills the regime so every business day in [start, end] has a value (regime persists from last FRED reading)

Add a CLI entry point: when run as `python -m src.regime.monitor`, print the current regime to stdout.

Tests in tests/regime/test_monitor.py:
- Mock the FREDClient.fetch_series to return a controlled pd.Series
- Verify all three threshold branches (GREEN, YELLOW, RED) using values 3.0, 4.5, 6.0
- Verify boundary values: 4.00 → YELLOW, 5.50 → YELLOW (not RED)
- Verify as_of semantics: pass a date and confirm it uses the value at or before that date, not after
- Verify get_regime_series forward-fills correctly across a 30-day window with only 5 underlying data points

Do not implement validation against historical drawdowns yet — that's Ticket 1.3.
```

**Verify:**
```bash
uv run pytest tests/regime/test_monitor.py -v
uv run python -m src.regime.monitor   # prints current regime
```

### Ticket 1.3 — Historical validation notebook

**Goal:** Prove the regime monitor would have caught 2008, 2020, and 2022 drawdowns. This is the master plan Phase 1 pass criteria.
**Deliverable:** `notebooks/01_regime_validation.ipynb`, validation report.

**Prompt:**
```
Create notebooks/01_regime_validation.ipynb that validates the regime monitor against historical SPY drawdowns per master_plan_v4.md Phase 1 pass criteria.

The notebook should:
1. Use get_regime_series() from src.regime.monitor for the period 2007-01-01 to 2024-12-31
2. Pull SPY daily closes for the same period (use yfinance for SPY only — this is acceptable for index validation, even though we won't trust yfinance for stock-level data later)
3. Compute SPY rolling drawdown: peak-to-current as a percentage
4. Plot two stacked subplots sharing x-axis:
   - Top: SPY price with shaded background regions colored by regime (green/yellow/red, alpha=0.2)
   - Bottom: SPY drawdown as percentage, with regime overlay
5. Compute and print the validation table — for each event below, show the date the regime first turned RED and the date SPY drawdown crossed -10%, plus the lead time in trading days:
   - 2008-09 (Lehman/GFC)
   - 2020-02/03 (COVID)
   - 2022 H1 (Fed tightening — show whether YELLOW or RED triggered, and when)
6. Write a markdown cell at the end summarizing PASS/FAIL against master plan criteria:
   - PASS if RED ≥ 5 trading days before drawdown crosses 10% in 2008-09 AND 2020
   - PASS if YELLOW or RED at some point in 2022 H1

Use the FREDClient and get_regime_series — do not bypass them. Save the figure to notebooks/figures/regime_validation.png.

If the validation FAILS, do not silently change thresholds. Report the failure and stop. The thresholds in master_plan_v4.md are locked.
```

**Verify:**
```bash
uv run jupyter nbconvert --to notebook --execute notebooks/01_regime_validation.ipynb --output 01_regime_validation_executed.ipynb
# Inspect the executed notebook and the figure manually.
# Acceptance: PASS markdown at the end confirms all three checkpoints.
```

---

# Sprint 2 — Universe Construction

**Sprint goal:** Build a survivorship-bias-free, point-in-time universe of S&P 500 stocks with $1B–$10B market cap.
**Duration:** Master plan: 2 weeks. Claude Code: 2–3 days.
**Definition of done:** Lehman Brothers test passes (present pre-Sept 2008, gone after).

### Ticket 2.1 — Historical S&P 500 constituent puller

**Goal:** Download and parse the fja05680/sp500 constituent change log into a clean lookup table.
**Deliverable:** `src/universe/constituents.py`, `data/processed/sp500_constituents.parquet`.

**Prompt:**
```
In src/universe/constituents.py, implement loading of the fja05680/sp500 historical constituents list from GitHub.

The fja05680 repo (https://github.com/fja05680/sp500) maintains a CSV file `S&P 500 Historical Components & Changes.csv` that lists, for each historical date, the full set of S&P 500 tickers as of that date. Each row is a (date, ticker) pair when a constituent change occurred.

Implement:
  def download_constituent_changes(force_refresh: bool = False) -> pd.DataFrame
    - Downloads the CSV from the raw GitHub URL into data/raw/sp500_changes.csv
    - If file exists and force_refresh is False, skip download
    - Returns a DataFrame with columns: date (datetime64[ns]), tickers (list[str])
    - Parses the comma-separated tickers field into a Python list
  
  def build_constituent_panel() -> pd.DataFrame
    - Calls download_constituent_changes()
    - Expands into a long-form DataFrame: one row per (date, ticker) pair
    - Forward-fills membership: if a ticker is in the list on date D and D+5, it's also in the list on D+1, D+2, D+3, D+4
    - Use a business-day calendar (pandas.bdate_range) for forward-filling, NOT calendar days
    - Returns columns: date (datetime64[ns]), ticker (str), in_index (bool, always True for these rows)
    - Saves to data/processed/sp500_constituents.parquet
    - Returns the DataFrame

Tests in tests/universe/test_constituents.py:
- Use a small fixture CSV stored at tests/fixtures/sp500_changes_sample.csv with 3-5 hand-crafted rows covering ticker additions and removals
- Mock the download to return the fixture
- Verify build_constituent_panel correctly forward-fills membership
- Verify a removed ticker disappears from the panel after its removal date

Do not pull live data in tests. Acceptance is that, when run end-to-end on the real fja05680 file, Lehman Brothers (LEH or LEHMQ) appears in the panel for dates in early 2008 and is absent after September 15, 2008.
```

**Verify:**
```bash
uv run pytest tests/universe/test_constituents.py -v
uv run python -c "
from src.universe.constituents import build_constituent_panel
df = build_constituent_panel()
leh_dates = df[df['ticker'].isin(['LEH','LEHMQ'])]['date']
print(f'LEH first seen: {leh_dates.min()}, last seen: {leh_dates.max()}')
print(f'Pass: {leh_dates.max() < pd.Timestamp(\"2008-12-01\")}')
"
```

### Ticket 2.2 — Market cap fetcher

**Goal:** For each (date, ticker) in the panel, attach a point-in-time market cap value.
**Deliverable:** `src/universe/market_cap.py`, `data/processed/market_caps.parquet`.

**Prompt:**
```
In src/universe/market_cap.py, implement market cap retrieval.

For Sprint 2 (free-tools phase), use yfinance for adjusted close prices and shares outstanding. We acknowledge yfinance has data quality issues; this is the documented Sprint 2 → Sprint 5 upgrade path per master_plan_v4.md.

Implement:
  def fetch_price_history(tickers: list[str], start: date, end: date) -> pd.DataFrame
    - Calls yfinance.download(tickers, start, end, auto_adjust=False, progress=False)
    - Returns a long-form DataFrame: date, ticker, close, adj_close, volume (one row per ticker-date)
    - Handles tickers that fail to download by logging a warning and excluding them — do not raise
    - Caches results in data/raw/prices/{ticker}.parquet (one file per ticker) so reruns don't re-download
  
  def fetch_shares_outstanding(ticker: str) -> pd.Series
    - Returns a pd.Series indexed by quarter-end date with shares outstanding values
    - Uses yfinance Ticker.quarterly_balance_sheet to extract 'Ordinary Shares Number' or equivalent
    - Returns empty Series if data unavailable, log warning
    - Cache to data/raw/shares/{ticker}.parquet
  
  def build_market_cap_panel(constituents: pd.DataFrame, start: date, end: date) -> pd.DataFrame
    - Takes the constituent panel from Ticket 2.1
    - For each unique ticker, fetches prices and shares
    - Forward-fills shares outstanding (quarterly cadence) onto daily price data
    - Computes market_cap_usd = close * shares_outstanding
    - Returns columns: date, ticker, close, shares_outstanding, market_cap_usd
    - Saves to data/processed/market_caps.parquet

Tests in tests/universe/test_market_cap.py:
- Mock yfinance.download and yfinance.Ticker
- Verify market cap calculation: close=100, shares=1_000_000 → market_cap_usd = 100_000_000
- Verify forward-fill of quarterly shares onto daily price data
- Verify failed tickers are skipped, not raised

Important: Add a clear FIXME comment at the top of the file noting that yfinance data quality is acknowledged-imperfect and the Sprint 5 deliverable replaces this with Polygon/Sharadar fundamentals data.

Stay in scope. Do not implement the universe filter (that's the next ticket).
```

**Verify:**
```bash
uv run pytest tests/universe/test_market_cap.py -v
# Smoke test: pull a small panel for AAPL/MSFT for 2023
uv run python -c "
from datetime import date
from src.universe.market_cap import fetch_price_history
df = fetch_price_history(['AAPL', 'MSFT'], date(2023,1,1), date(2023,2,1))
print(df.head())
print(f'Rows: {len(df)}')
"
```

### Ticket 2.3 — Universe filter and Lehman test

**Goal:** Filter the constituent panel to $1B–$10B market cap. Validate with Lehman.
**Deliverable:** `src/universe/builder.py`, `data/processed/universe.parquet`, `notebooks/02_universe_validation.ipynb`.

**Prompt:**
```
In src/universe/builder.py, implement the universe builder per master_plan_v4.md Phase 2.

Function:
  def build_universe(start: date, end: date,
                     min_mcap: float = 1_000_000_000,
                     max_mcap: float = 10_000_000_000) -> pd.DataFrame
    - Loads the constituent panel (Ticket 2.1) and market cap panel (Ticket 2.2)
    - Inner-joins them on (date, ticker)
    - Filters rows where min_mcap <= market_cap_usd <= max_mcap
    - Returns columns: date, ticker, market_cap_usd
    - Saves to data/processed/universe.parquet
    - Logs counts: total constituent-days, days passing market cap filter, unique tickers

Tests in tests/universe/test_builder.py:
- Construct fixture DataFrames for constituents and market caps
- Verify the join + filter produces the expected output
- Verify market cap thresholds are inclusive at both bounds
- Verify a ticker that was IN the index but had market cap outside the range is correctly excluded

Then create notebooks/02_universe_validation.ipynb that runs the master plan Phase 2 acceptance test:
1. Build the universe for 2007-01-01 to 2009-12-31 (use a wider mcap window for this test: $500M to $50B since LEH was a large-cap)
2. Filter to ticker in ['LEH', 'LEHMQ']
3. Print the dates LEH appears in the universe
4. PASS criteria: LEH appears in 2007-2008 dates AND does not appear in any date after 2008-09-15
5. Also print summary statistics for the actual production universe ($1B–$10B): total rows, unique tickers, date range, count by year

Output a markdown cell at the end with PASS/FAIL.
```

**Verify:**
```bash
uv run pytest tests/universe/test_builder.py -v
uv run jupyter nbconvert --to notebook --execute notebooks/02_universe_validation.ipynb --output 02_universe_validation_executed.ipynb
```

---

# Sprint 3 — SUE Engine

**Sprint goal:** Compute Standardized Unexpected Earnings using point-in-time correct EPS data and sector-pooled MAD denominator.
**Duration:** Master plan: 2 weeks. Claude Code: 3–4 days.
**Definition of done:** SUE distribution roughly symmetric around 0; top-decile beats bottom-decile by ≥50bps on day +1.

### Ticket 3.1 — SEC EDGAR client

**Goal:** Polite, rate-limited EDGAR client for fetching 8-K filings (where companies announce earnings).
**Deliverable:** `src/signals/edgar_client.py`, tests.

**Prompt:**
```
In src/signals/edgar_client.py, implement an SEC EDGAR API client.

Requirements per SEC's fair-access guidelines:
- All requests MUST include a User-Agent header (use settings.sec_edgar_user_agent)
- Rate-limit: max 10 requests per second (use a token bucket or simple time.sleep gate)
- Handle 429 responses with exponential backoff (start at 1s, double up to 60s, max 5 retries)

Class EDGARClient:
  __init__(self, user_agent: str | None = None)
  
  def get_company_filings(self, cik: str, form_types: list[str], 
                          start: date | None = None, end: date | None = None) -> pd.DataFrame
    - Endpoint: https://data.sec.gov/submissions/CIK{cik:0>10}.json
    - Parse the recent filings array
    - Filter to form_types (e.g. ['8-K'])
    - Filter by filing date range if provided
    - Return DataFrame: cik, ticker, form_type, filing_date, accession_number, primary_document_url
  
  def get_ticker_to_cik_map(self) -> dict[str, str]
    - Endpoint: https://www.sec.gov/files/company_tickers.json
    - Returns dict mapping ticker (uppercase) -> 10-digit zero-padded CIK string
    - Cache the result in memory; SEC updates this daily so don't refetch within a process

Custom exception EDGARFetchError for any non-recoverable failure.

Tests in tests/signals/test_edgar_client.py:
- Use pytest-mock to patch requests.get
- Verify User-Agent header is sent
- Verify rate-limiting sleeps between rapid calls
- Verify 429 triggers retry with backoff (use mock_clock or freezegun)
- Verify get_company_filings parses the JSON correctly using a fixture

DO NOT hit live SEC in tests. Save a fixture JSON file at tests/fixtures/edgar_aapl_submissions.json with a realistic-shaped sample (you can write a one-off script to fetch it, but commit only the fixture).

Stay strictly in scope: this is the HTTP client only. No earnings parsing, no SUE math.
```

**Verify:**
```bash
uv run pytest tests/signals/test_edgar_client.py -v
# Smoke test (one-time, real API):
uv run python -c "
from src.signals.edgar_client import EDGARClient
c = EDGARClient()
m = c.get_ticker_to_cik_map()
print(f'AAPL CIK: {m[\"AAPL\"]}')  # should be 0000320193
"
```

### Ticket 3.2 — 8-K earnings announcement parser

**Goal:** Extract actual reported EPS from 8-K filings (Item 2.02 — Results of Operations).
**Deliverable:** `src/signals/earnings_actuals.py`, tests.

**Prompt:**
```
In src/signals/earnings_actuals.py, implement extraction of actual reported EPS from SEC 8-K filings.

This is hard. 8-Ks are unstructured HTML. Be honest about the limits.

Strategy:
1. For each ticker, get all 8-K filings via EDGARClient
2. Filter to filings that include Item 2.02 (Results of Operations and Financial Condition) — this is in the filing's items list in the JSON metadata
3. For each candidate filing, fetch the primary document URL
4. Parse the HTML using BeautifulSoup. Look for diluted EPS in the body. Common patterns:
   - "Diluted earnings per share" followed by a dollar amount
   - Tables with rows labeled "Diluted EPS" or "Net income per diluted share"
5. Return a structured record

Function:
  def fetch_earnings_actuals(ticker: str, start: date, end: date,
                             client: EDGARClient | None = None) -> pd.DataFrame
    - Returns columns: ticker, filing_date, period_end_estimated, actual_eps_diluted, source_url, parse_confidence
    - parse_confidence is one of "HIGH" (clean table extraction), "MEDIUM" (regex match in text), "LOW" (heuristic guess), "FAILED" (could not extract)
    - Always include filing_date — never period_end as a stand-in (the master plan is explicit on this)

Add `uv add beautifulsoup4 lxml requests` to project dependencies.

Tests in tests/signals/test_earnings_actuals.py:
- Use 3-5 fixture HTML files at tests/fixtures/8k_samples/ representing real-world variants you find online
- Verify HIGH-confidence extraction on a clean tabular 8-K
- Verify MEDIUM-confidence extraction on a prose 8-K
- Verify FAILED is returned (not raised) when EPS cannot be found
- Verify filing_date is always populated, never null

Important: This is acknowledged best-effort parsing. Add a top-of-file FIXME noting that Sprint 5 replaces this with Polygon's earnings endpoint, which is point-in-time clean and structured. The Sprint 3 implementation gives directional sanity-check data, not production-grade input.

Do not implement SUE calculation — that's Ticket 3.4.
```

**Verify:**
```bash
uv run pytest tests/signals/test_earnings_actuals.py -v
# Smoke test on a small ticker set:
uv run python -c "
from datetime import date
from src.signals.earnings_actuals import fetch_earnings_actuals
df = fetch_earnings_actuals('AAPL', date(2023,1,1), date(2024,1,1))
print(df)
"
```

### Ticket 3.3 — yfinance estimate fetcher (acknowledged-imperfect)

**Goal:** Pull consensus EPS estimates from yfinance with quality flags.
**Deliverable:** `src/signals/earnings_estimates.py`, tests.

**Prompt:**
```
In src/signals/earnings_estimates.py, implement consensus EPS estimate retrieval via yfinance.

This is acknowledged-imperfect (master_plan_v4.md Phase 3 watch-out: "yfinance estimate data is ~70% reliable — flag stocks where coverage is missing rather than dropping silently"). Do not silently skip missing data.

Function:
  def fetch_earnings_estimates(ticker: str) -> pd.DataFrame
    - Uses yfinance.Ticker(ticker).earnings_history (or .earnings_dates if that's been deprecated by yfinance — check the current yfinance API)
    - Returns columns: ticker, period_end (datetime64[ns]), estimate_eps (float), reported_eps (float), surprise_pct, data_quality
    - data_quality is "OK" if the row has both estimate and reported, "MISSING_ESTIMATE" if estimate is null, "MISSING_REPORTED" if reported is null, "STALE" if more than 5 years old
    - On any yfinance failure, return an empty DataFrame with correct schema and log a warning — do not raise
    - Cache results in data/raw/estimates/{ticker}.parquet (one file per ticker, refreshed monthly)

Add a clear FIXME at the top of the file noting that this data is point-in-time contaminated (the "estimate" Yahoo shows today may not be what the consensus actually was the day before earnings) and Sprint 5 replaces it.

Tests in tests/signals/test_earnings_estimates.py:
- Mock yfinance.Ticker
- Verify all four data_quality values are correctly assigned
- Verify failed yfinance call returns empty DataFrame, does not raise
- Verify caching: second call with cached file does not re-invoke yfinance

Stay in scope.
```

**Verify:**
```bash
uv run pytest tests/signals/test_earnings_estimates.py -v
```

### Ticket 3.4 — `compute_sue()` with sector-pooled MAD

**Goal:** The actual SUE calculation per master plan Phase 3 — using sector-pooled MAD as denominator (not per-stock std).
**Deliverable:** `src/signals/sue.py`, tests, validation notebook.

**Prompt:**
```
In src/signals/sue.py, implement the SUE calculation per master_plan_v4.md Phase 3 (revised v4 spec, NOT v3).

Critical: Use sector-pooled MAD (median absolute deviation), NOT per-stock std. This is the v4 fix for the "8-quarter denominator instability" flaw.

Steps:
1. Build a function load_sector_map() that returns a dict[ticker, str] of GICS sector. For Sprint 3, use yfinance Ticker.info['sector'] (acknowledged-imperfect). Cache to data/processed/sector_map.parquet. Add a FIXME noting Sprint 5 replaces this with proper GICS data.

2. Build a function compute_sector_mad_table(estimates_actuals: pd.DataFrame, sectors: dict, min_observations: int = 50) -> pd.DataFrame:
    - Joins estimates with actuals on (ticker, period_end) — using filing_date from actuals as the "as_of" reference
    - Computes raw_surprise = actual_eps - estimate_eps for each (ticker, period)
    - Groups by sector
    - For each sector, computes the MAD of raw_surprise: median(|surprise - median(surprise)|)
    - Requires at least min_observations surprises per sector or returns NaN for that sector
    - Returns DataFrame: sector, mad, n_observations
    - Saves to data/processed/sector_mad.parquet

3. The main function:
    def compute_sue(ticker: str, earnings_filing_date: date,
                    sector_mad_table: pd.DataFrame,
                    actuals: pd.DataFrame,
                    estimates: pd.DataFrame,
                    sectors: dict[str, str]) -> float | None
    - Find the actual EPS for this ticker at this filing_date
    - Find the estimate EPS for the same period_end
    - Compute raw surprise
    - Look up the sector for this ticker
    - Look up the sector MAD from sector_mad_table
    - Return surprise / (1.4826 * sector_mad) — the 1.4826 makes MAD a consistent estimator of std for normal distributions
    - Return None if any input is missing — do not silently substitute zeros

Critical: The point-in-time discipline. Both actuals and estimates passed in must be filtered to filing_date <= earnings_filing_date BEFORE calling compute_sue. Add a defensive assertion inside compute_sue that any actuals.filing_date > earnings_filing_date raises ValueError. This catches leak bugs early.

Tests in tests/signals/test_sue.py:
- Construct fixture data: 5 sectors × 60 surprises each, with one outlier sector having one synthetic surprise of magnitude 50
- Verify the outlier does NOT distort the sector's MAD significantly (this is the whole point of MAD over std)
- Verify a ticker missing from sector_map returns None, does not raise
- Verify the leak guard: passing actuals with filing_date > earnings_filing_date raises ValueError
- Verify the 1.4826 scaling factor is applied

Stay in scope. Do NOT build the multi-signal composite (Sprint 4) or any percentile ranking yet.
```

**Verify:**
```bash
uv run pytest tests/signals/test_sue.py -v
```

### Ticket 3.5 — SUE validation notebook

**Goal:** Master plan Phase 3 pass criteria: distribution shape, outlier robustness, top-vs-bottom decile sanity check.
**Deliverable:** `notebooks/03_sue_validation.ipynb`.

**Prompt:**
```
Create notebooks/03_sue_validation.ipynb that validates the SUE engine per master_plan_v4.md Phase 3 pass criteria.

The notebook should:

1. Load the universe (Sprint 2 output) for 2018-01-01 to 2022-12-31
2. For each ticker in the universe, fetch earnings actuals (Ticket 3.2) and estimates (Ticket 3.3)
3. Build the sector MAD table (Ticket 3.4)
4. Compute SUE for every (ticker, earnings_event) in the data

5. Distribution check:
   - Plot histogram of SUE values
   - Print mean, median, std, skew
   - PASS if mean is within ±0.2 and the distribution is roughly symmetric (skew between -1 and +1)
   - The master plan v4 explicitly corrects v3 here: SUE should be roughly symmetric around 0, not "right tailed"

6. Outlier robustness check:
   - Inject a synthetic SUE = 100 into a single ticker-date
   - Recompute percentile ranks across the universe
   - Verify the percentile rank distribution of the OTHER stocks is unchanged
   - PASS if max percentile-rank shift among non-injected stocks is < 0.005

7. Day +1 sanity check (the "does the signal exist at all" test):
   - For every earnings event, compute the day+1 forward return (close on filing_date+1 / close on filing_date - 1)
   - Use yfinance for prices (acknowledged-imperfect, Sprint 2 caveat applies)
   - Bucket events into deciles by SUE
   - Plot mean day+1 return by decile
   - PASS if (top decile mean - bottom decile mean) >= 0.005 (50 bps)

8. Final markdown cell with PASS/FAIL on each of the three criteria.

If any criterion FAILS, do not adjust thresholds to make it pass. Report the failure and stop. The master plan is locked.
```

**Verify:**
```bash
uv run jupyter nbconvert --to notebook --execute notebooks/03_sue_validation.ipynb --output 03_sue_validation_executed.ipynb
# Inspect notebook output for three PASS markers.
```

---

# Sprint 4 — Multi-Signal Composite

**Sprint goal:** Add analyst revision + insider buying signals; combine via percentile rank with equal weights.
**Duration:** Master plan: 2 weeks. Claude Code: 2–3 days.
**Definition of done:** Top-decile composite outperforms bottom-decile by ≥75bps over 5–15 day hold; outlier-stable; no look-ahead leaks.

### Ticket 4.1 — Analyst revision signal

**Goal:** Score analyst upgrade/downgrade activity in the 10 days following earnings.
**Deliverable:** `src/signals/revisions.py`, tests.

**Prompt:**
```
In src/signals/revisions.py, implement the analyst revision signal per master_plan_v4.md Phase 4.

Use yfinance Ticker.recommendations as the data source (acknowledged-imperfect; Sprint 5 replaces with Benzinga/Polygon).

Function:
  def fetch_revisions(ticker: str) -> pd.DataFrame
    - Returns columns: ticker, date, firm, action_type, from_grade, to_grade
    - action_type values: "upgrade", "downgrade", "initiation_buy", "initiation_sell", "initiation_neutral", "pt_raise", "pt_cut", "maintain"
    - Maps yfinance's raw fields into these normalized values
    - Cache to data/raw/revisions/{ticker}.parquet
    - Returns empty DataFrame on yfinance failure (log warning, don't raise)
  
  def compute_revision_score(ticker: str, earnings_filing_date: date,
                             window_days: int = 10,
                             revisions_df: pd.DataFrame | None = None) -> float
    - If revisions_df is None, fetch via fetch_revisions
    - Filter to revisions where: filing_date < date <= filing_date + window_days
    - Critically: filter to date > earnings_filing_date (forward-only window) AND date <= as_of_date passed in (no look-ahead in backtest)
    - Score per master_plan_v3 Signal 2 weighting (this part survives from v3 unchanged):
        upgrade: +2
        initiation_buy: +2
        pt_raise: +1
        downgrade: -2
        initiation_sell: -2
        pt_cut: -2
        initiation_neutral, maintain: 0
    - Return the sum

Add a backtest-friendly function:
  def compute_revision_score_panel(events: pd.DataFrame, window_days: int = 10) -> pd.DataFrame
    - events has columns: ticker, earnings_filing_date
    - Returns events with added column: revision_score
    - Vectorized — does not call compute_revision_score per row in a loop unless necessary

Tests in tests/signals/test_revisions.py:
- Construct fixture revisions data: 5 tickers, 20 revisions each
- Verify the score weighting matches the spec exactly
- Verify the window is forward-only and respects window_days
- Verify look-ahead leak guard: revisions after as_of_date are excluded

Stay in scope. Do not implement insider scoring or composite.
```

**Verify:**
```bash
uv run pytest tests/signals/test_revisions.py -v
```

### Ticket 4.2 — Insider buying signal

**Goal:** Score insider buying via SEC Form 4, 180-day lookback, $50k floor, exclude 10b5-1 plans.
**Deliverable:** `src/signals/insider.py`, tests.

**Prompt:**
```
In src/signals/insider.py, implement the insider buying signal per master_plan_v4.md Phase 4.

Use SEC EDGAR Form 4 filings via the EDGARClient from Ticket 3.1.

Form 4 filings are XML. The EDGAR Form 4 XML schema includes:
- Issuer (company): cik, ticker
- Reporting Person (insider): name, role (officer/director/10% owner)
- Transactions: transactionCode, securitiesTransacted (shares), transactionPricePerShare, plan_type indicator (10b5-1 yes/no)

For Sprint 4, prefer the openinsider.com aggregated daily feed (free, parses Form 4s for you). It exposes a CSV download endpoint per ticker. Use that as the primary source. Fall back to raw EDGAR parsing only if openinsider data is missing.

Implement:
  def fetch_insider_transactions(ticker: str, start: date, end: date) -> pd.DataFrame
    - Returns: ticker, filing_date, insider_name, role, transaction_code, shares, price_per_share, value_usd, is_10b5_1
    - role normalized to one of: "CEO", "CFO", "COO", "President", "Director", "10%Owner", "Other"
    - transaction_code: "P" (open market buy), "S" (sale), "A" (grant), "M" (option exercise), etc.
    - Cache to data/raw/insider/{ticker}.parquet
  
  def compute_insider_score(ticker: str, as_of_date: date,
                            lookback_days: int = 180,
                            min_value_usd: float = 50_000,
                            transactions_df: pd.DataFrame | None = None) -> float
    - Filter to: as_of_date - lookback_days < filing_date < as_of_date (strict <, no same-day data)
    - Filter to: transaction_code == "P" (open-market buys only)
    - Filter to: value_usd >= min_value_usd
    - Filter to: is_10b5_1 == False (exclude scheduled plans)
    - Score per master_plan_v3 Signal 3 weighting:
        CEO/CFO/COO/President buy: +3
        Director/10%Owner/Other: +1
    - Return sum

  def compute_insider_score_panel(events: pd.DataFrame, lookback_days: int = 180,
                                  min_value_usd: float = 50_000) -> pd.DataFrame
    - events has columns: ticker, as_of_date
    - Returns events with added column: insider_score

Tests in tests/signals/test_insider.py:
- Fixture transactions data covering all transaction codes, all role types, mix of 10b5-1 and non-plan
- Verify only "P" code is counted
- Verify 10b5-1 trades are excluded
- Verify $50k floor is inclusive
- Verify the lookback window is correct (180 days strictly before as_of_date)
- Verify role-based weighting is exactly correct (3 for CEO, 1 for Director)
- Verify the leak guard: transactions filed on or after as_of_date are excluded

Stay in scope. No composite yet.
```

**Verify:**
```bash
uv run pytest tests/signals/test_insider.py -v
```

### Ticket 4.3 — `master_alpha_score()` composite

**Goal:** Combine the three signals via percentile rank with equal weights, with absolute threshold filter.
**Deliverable:** `src/signals/composite.py`, tests.

**Prompt:**
```
In src/signals/composite.py, implement the master alpha score per master_plan_v4.md Phase 4.

Use master plan v4 specs (NOT v3). Key changes from v3:
- Equal weights: 0.33/0.33/0.33 (NOT 0.50/0.35/0.15)
- Absolute threshold: alpha_score > 0.70 alongside top-N selection (NOT just nlargest)

Function:
  def master_alpha_score(universe_df: pd.DataFrame, as_of_date: date,
                         actuals_df: pd.DataFrame,
                         estimates_df: pd.DataFrame,
                         revisions_df: pd.DataFrame,
                         insider_df: pd.DataFrame,
                         sector_mad_table: pd.DataFrame,
                         sector_map: dict[str, str],
                         w_sue: float = 1/3,
                         w_revision: float = 1/3,
                         w_insider: float = 1/3) -> pd.DataFrame
    - For each ticker in the universe (filtered to universe membership on as_of_date):
        - Compute SUE (Ticket 3.4) using earnings_filing_date <= as_of_date
        - Compute revision_score (Ticket 4.1) using window after earnings_filing_date but <= as_of_date
        - Compute insider_score (Ticket 4.2) using lookback ending at as_of_date
    - Apply percentile rank (rank(pct=True)) to each raw signal across the cross-section
    - Compute alpha_score = w_sue*sue_pct + w_revision*revision_pct + w_insider*insider_pct
    - Return a DataFrame with ALL universe tickers and columns: ticker, sue_raw, sue_pct, revision_raw, revision_pct, insider_raw, insider_pct, alpha_score
    - Sort by alpha_score descending
    - Important: validate that w_sue + w_revision + w_insider == 1.0 (use math.isclose with abs_tol=1e-9), raise ValueError if not

  def select_candidates(scored_df: pd.DataFrame, top_n: int = 10,
                        min_score: float = 0.70) -> pd.DataFrame
    - Apply BOTH filters:
        scored_df[scored_df['alpha_score'] >= min_score].nlargest(top_n, 'alpha_score')
    - Returns 0 to top_n rows. Empty result is valid behavior (no trades that day).
    - Log the count: "Selected {n} candidates from {universe_size} (threshold={min_score}, top_n={top_n})"

Critical implementation note: this function will be called many thousands of times in backtest. Vectorize where possible. Pass in pre-loaded data frames; do not refetch inside the function.

Tests in tests/signals/test_composite.py:
- Build fixture data with 100 synthetic tickers, hand-set raw signal values
- Verify percentile rank assigns 1.0 to the top stock and 0.0 (or 1/n) to the bottom
- Verify equal-weight composite formula
- Verify weights summing to !=1 raises ValueError
- Verify select_candidates with min_score=0.70 returns 0 candidates when all alpha_scores are below 0.70
- Verify the leak guards in the underlying signal calls are respected (use mock to verify as_of_date is passed through correctly)

Stay in scope.
```

**Verify:**
```bash
uv run pytest tests/signals/test_composite.py -v
```

### Ticket 4.4 — Composite validation notebook

**Goal:** Master plan Phase 4 pass criteria.
**Deliverable:** `notebooks/04_composite_validation.ipynb`.

**Prompt:**
```
Create notebooks/04_composite_validation.ipynb that validates master_alpha_score per master_plan_v4.md Phase 4 pass criteria.

Steps:

1. Load universe (Sprint 2) for 2018-01-01 to 2022-12-31
2. Load all signal inputs: actuals (3.2), estimates (3.3), revisions (4.1), insider (4.2), sector MAD (3.4), sector map
3. For each Friday in the date range, run master_alpha_score with as_of_date = that Friday
4. Collect all (date, ticker, alpha_score) triples into a panel

5. Top-decile vs bottom-decile check:
   - For each scoring date, bucket tickers into deciles by alpha_score
   - For tickers in top decile and bottom decile, compute the forward 5-to-15-day return (mean over the 11-day hold)
   - Compute the average forward return per decile across all scoring dates
   - PASS if (top decile - bottom decile) >= 0.0075 (75 bps)

6. Outlier stability check:
   - For one scoring date in 2020, inject a synthetic SUE of 100 into a single ticker
   - Recompute the alpha_scores and percentile ranks
   - Verify the percentile-rank shift on OTHER stocks is < 0.005
   - PASS if confirmed

7. Look-ahead leak audit:
   - Pick 5 random scoring dates
   - For each, manually verify (in code, with assertions) that ALL data feeding into alpha_score is timestamped <= as_of_date
   - Specifically: actuals.filing_date <= as_of_date, revisions.date <= as_of_date, insider.filing_date < as_of_date
   - PASS if no leaks

8. Top-N selection sparsity check:
   - For each scoring date, run select_candidates(top_n=10, min_score=0.70)
   - Count days with 0 candidates (should be many — this is correct behavior in weak earnings periods)
   - Plot histogram of candidate counts per day
   - There is no PASS/FAIL on this — it's an observation. But if EVERY day has 10 candidates, something is wrong (the threshold is not biting).

9. Final markdown cell with PASS/FAIL on the three hard criteria.

If any criterion fails, stop. Do not adjust weights or thresholds to force a pass.
```

**Verify:**
```bash
uv run jupyter nbconvert --to notebook --execute notebooks/04_composite_validation.ipynb --output 04_composite_validation_executed.ipynb
```

---

# Sprint 5 — Backtest Infrastructure

**Sprint goal:** Replace yfinance/EDGAR data with Polygon (paid, clean), build the backtest engine with realistic costs and gap-risk modeling, run walk-forward validation 2015–2023.
**Duration:** Master plan: 6 weeks. Claude Code: 1–2 weeks.
**Cost gate:** Subscribe to **Polygon.io Starter ($29/mo) BEFORE this sprint.** Do not start without it.
**Definition of done:** Walk-forward Sharpe > 1.3 in ≥5 of 6 test years, max DD < 25%, win rate 45–55%.

### Ticket 5.1 — Polygon.io client and data swap

**Goal:** Replace yfinance with Polygon for prices, fundamentals, earnings.
**Deliverable:** `src/data/polygon_client.py`, refactored `market_cap.py`, `earnings_actuals.py`, `earnings_estimates.py`.

**Prompt:**
```
Add `uv add polygon-api-client` to the project.

Create src/data/polygon_client.py wrapping the official polygon-api-client. Required endpoints:
  - /v2/aggs/ticker/{ticker}/range/1/day  (daily OHLCV)
  - /vX/reference/financials                (point-in-time fundamentals including EPS)
  - /v3/reference/tickers/{ticker}          (shares outstanding, market cap)

Class PolygonClient:
  - __init__ uses settings.polygon_api_key
  - fetch_daily_bars(ticker, start, end) -> pd.DataFrame  [date, ticker, open, high, low, close, volume, vwap]
  - fetch_financials(ticker, filing_date_from, filing_date_to) -> pd.DataFrame  [ticker, filing_date, period_end, eps_diluted_actual, ...]
  - fetch_share_classes(ticker) -> pd.DataFrame  [date, shares_outstanding]

Reasonable rate limiting (Polygon Starter is 5 calls/minute on REST). Use a token bucket. Cache aggressively to data/raw/polygon/.

Then refactor:
  - src/universe/market_cap.py: add a parameter `provider: Literal["yfinance", "polygon"] = "polygon"`. Default to polygon. Keep yfinance code path for fallback but mark it deprecated.
  - src/signals/earnings_actuals.py: same pattern. The polygon path should fully replace the EDGAR-HTML-parsing path with structured data.
  - src/signals/earnings_estimates.py: Polygon Starter does NOT include consensus estimates. So estimates_path stays on yfinance for now, but add a TODO noting that estimates can be sourced from Tiingo or via a separate Sharadar SF1 subscription. For Sprint 5 backtest, this means SUE is computed against actuals from Polygon (clean) and estimates from yfinance (acknowledged-imperfect). Document this clearly in the file header. This is the honest state.

Tests in tests/data/test_polygon_client.py:
- Mock the polygon-api-client
- Verify rate limiting throttles correctly
- Verify each method returns the expected DataFrame schema

Update tests for the refactored modules. Use parameterized tests to cover both provider paths.

Stay in scope. Do not touch the backtest engine yet.
```

**Verify:**
```bash
uv run pytest tests/data tests/universe tests/signals -v
# Confirm all green.
```

### Ticket 5.2 — Position sizing module

**Goal:** ATR-based 1%-risk position sizing per master plan risk rules.
**Deliverable:** `src/backtest/position_sizing.py`, tests.

**Prompt:**
```
In src/backtest/position_sizing.py, implement the position sizing logic per master_plan_v4.md risk rules.

Functions:
  def compute_atr(prices: pd.DataFrame, ticker: str, as_of_date: date, period: int = 14) -> float | None
    - prices is the daily OHLC DataFrame
    - Computes the 14-day Wilder ATR ending at as_of_date (exclusive — only data BEFORE as_of_date)
    - Returns None if insufficient history
    - Use the standard formula: TR = max(high-low, |high-prev_close|, |low-prev_close|), ATR = exponential moving average of TR

  def position_size(portfolio_value: float, entry_price: float, atr_14: float,
                    risk_pct: float = 0.01, atr_multiplier: float = 2.5,
                    max_position_pct: float = 0.15) -> dict
    - Stop distance = atr_multiplier * atr_14
    - Max risk dollars = portfolio_value * risk_pct
    - Raw shares = floor(max_risk_dollars / stop_distance)
    - Position value = shares * entry_price
    - If position_value > portfolio_value * max_position_pct, cap shares = floor(portfolio_value * max_position_pct / entry_price)
    - Returns: {shares: int, stop_price: float, position_value_usd: float, capped_by: "risk" | "max_position"}

Tests in tests/backtest/test_position_sizing.py:
- Verify the master plan example: $20k portfolio, $50 entry, $4 ATR → 20 shares, $1000 position, stop at $40
- Verify the calmer-stock example: $1 ATR → would be 80 shares ($4000) but capped at 15% = $3000 = 60 shares, capped_by="max_position"
- Verify None ATR raises ValueError (or returns clear empty result)
- Verify negative or zero ATR raises ValueError

Stay in scope.
```

**Verify:**
```bash
uv run pytest tests/backtest/test_position_sizing.py -v
```

### Ticket 5.3 — Trade simulator with gap-risk

**Goal:** Simulate fills, stops, and exits including the master plan v4 gap-risk fix.
**Deliverable:** `src/backtest/simulator.py`, tests.

**Prompt:**
```
In src/backtest/simulator.py, implement single-trade simulation with the v4 gap-risk fix.

Function:
  def simulate_trade(ticker: str, entry_date: date, entry_price: float, shares: int,
                     stop_price: float, max_hold_days: int = 15,
                     prices: pd.DataFrame, regime_series: pd.Series,
                     transaction_cost_bps: float = 12.5) -> dict
    - prices is daily OHLC for this ticker covering entry_date through entry_date + 30 days
    - For each day from entry_date+1 to entry_date+max_hold_days:
        - Check regime: if regime_series.loc[day] == "RED", exit at next open (close all positions on regime flip)
        - Check gap-down: if open < stop_price, fill at OPEN price (NOT at stop_price). This is the master plan v4 gap-risk fix.
        - Otherwise, if low <= stop_price during the day, fill at stop_price
        - Check abnormal-gain partial exit: if cumulative return >= 20% within 5 days of entry, mark a 50% partial exit at that day's close, leave 50% to ride
        - Otherwise hold
    - On day = entry_date + max_hold_days: exit at close (time-based exit, unconditional)
    - Apply transaction_cost_bps on entry AND on each exit (so a partial-exit + final-exit trade pays costs three times: entry + partial-exit + final-exit)
    - Return: {entry_date, exit_date, entry_price, exit_price, shares, gross_pnl, transaction_costs, net_pnl, exit_reason: "STOP" | "GAP_THROUGH" | "REGIME_RED" | "TIME_15" | "PARTIAL_THEN_TIME_15"}

Tests in tests/backtest/test_simulator.py:
- Build fixture price series for several scenarios:
  1. Smooth winner: hits day 15 with +5% return
  2. Smooth loser: hits stop intraday on day 4
  3. Gap-through: opens day 7 below stop_price → exit at open (verify gap_through pnl is WORSE than the stop_price would imply — this is the v4 fix)
  4. Regime red: regime turns RED on day 6 → exit at day 7 open
  5. Abnormal gain: hits +25% on day 3 → 50% partial at day 3 close, remaining 50% rides to day 15
- Verify net_pnl correctly nets transaction costs
- Verify exit_reason is correct for each scenario

Stay in scope. Do NOT build the portfolio-level backtest engine yet.
```

**Verify:**
```bash
uv run pytest tests/backtest/test_simulator.py -v
```

### Ticket 5.4 — Portfolio-level backtest engine

**Goal:** Daily loop that scans candidates, sizes positions, manages portfolio, tracks equity curve.
**Deliverable:** `src/backtest/engine.py`, tests.

**Prompt:**
```
In src/backtest/engine.py, build the portfolio-level backtest engine.

Function:
  def run_backtest(start: date, end: date,
                   universe_path: Path,
                   actuals_df: pd.DataFrame,
                   estimates_df: pd.DataFrame,
                   revisions_df: pd.DataFrame,
                   insider_df: pd.DataFrame,
                   prices_df: pd.DataFrame,
                   regime_series: pd.Series,
                   sector_mad_table: pd.DataFrame,
                   sector_map: dict,
                   initial_capital: float = 100_000,
                   max_positions: int = 8,
                   max_sector_concentration: float = 0.20,
                   risk_pct: float = 0.01,
                   atr_multiplier: float = 2.5,
                   min_alpha_score: float = 0.70,
                   transaction_cost_bps: float = 12.5) -> BacktestResult

  BacktestResult is a dataclass with: trades_df, equity_curve, metrics_dict

Daily loop (each business day from start to end):
1. Check regime via regime_series. If RED → close all open positions at next open, no new entries today.
2. If YELLOW → use 50% of normal position size for any new entries.
3. For closing positions: each open position has its day-by-day simulation already running (use simulate_trade). At each day, advance the simulation by one day. Aggregate exits and update cash.
4. For new entries: 
   - Score the universe (master_alpha_score)
   - Apply select_candidates(top_n=8 - currently_open, min_score=0.70)
   - For each candidate, check sector concentration: skip if adding this position would push sector exposure above max_sector_concentration
   - Compute ATR; size with position_size
   - Record the entry; orders fill at next-day's opening-range pullback proxy: (next_open + next_day_low_first_30min) / 2 — for backtest, use (open + low) / 2 as a simple approximation. Document this clearly.
5. Update equity curve: cash + sum of mark-to-market position values

Critical: pass as_of_date carefully into all signal computations. Look-ahead is the #1 backtest bug.

Add three consecutive stop-out pause: if 3 stops fire in a row, pause new entries for 5 trading days.

Tests in tests/backtest/test_engine.py:
- Construct a small synthetic universe (10 tickers, 6 months of data)
- Run a backtest end-to-end
- Verify the equity curve is monotonically non-NaN
- Verify regime RED windows have no new entries and zero open positions
- Verify sector concentration cap is enforced
- Verify the 3-stop pause activates correctly
- Verify the trade log captures every entry and exit

Stay focused on engine correctness. Performance metrics computation is the next ticket.
```

**Verify:**
```bash
uv run pytest tests/backtest/test_engine.py -v
```

### Ticket 5.5 — Walk-forward harness + metrics

**Goal:** Walk-forward validation 2015–2023, holding out 2024–2025, with full metrics.
**Deliverable:** `src/backtest/walk_forward.py`, `src/backtest/metrics.py`, validation notebook.

**Prompt:**
```
In src/backtest/metrics.py, implement performance metrics:
  def compute_metrics(equity_curve: pd.Series, trades_df: pd.DataFrame, 
                      risk_free_rate: float = 0.04) -> dict
    - sharpe (annualized, using daily returns from equity curve)
    - sortino
    - max_drawdown (peak-to-trough as percentage)
    - calmar (annual_return / max_drawdown)
    - win_rate
    - avg_win_pct, avg_loss_pct
    - profit_factor (sum_wins / abs(sum_losses))
    - n_trades
    - avg_holding_days
    - turnover_per_year

In src/backtest/walk_forward.py, implement the walk-forward harness:
  def run_walk_forward(start_year: int = 2015, end_year: int = 2023,
                       train_min_years: int = 3, **kwargs) -> pd.DataFrame
    - Splits 2015–2023 into expanding-window train/test pairs:
      Train 2015-2017 → Test 2018
      Train 2015-2018 → Test 2019
      ... etc through Train 2015-2022 → Test 2023
    - 2024-2025 is held out, NEVER touched in this function
    - For each fold:
      - Fit any parameters that need fitting (currently: nothing, weights are fixed at equal — but the harness should support future fits)
      - Run run_backtest on the test year
      - Compute metrics
    - Returns a DataFrame: one row per fold with metrics

Then create notebooks/05_walk_forward_validation.ipynb:
1. Run walk-forward 2015-2023
2. Plot:
   - Equity curve concatenated across all test years
   - Sharpe per test year (bar chart)
   - Drawdown per test year
3. Print the master_plan_v4 Phase 5 pass criteria check:
   - PASS if Sharpe > 1.3 in ≥5 of 6 test years (after 25 bps round-trip costs)
   - PASS if max drawdown < 25% in worst year
   - PASS if no single year's Sharpe is > 2× the median (luck check)
   - PASS if win rate is in 45-55% range
4. Final markdown cell: PASS/FAIL on each of the four criteria.

Critical: This notebook must NOT touch 2024 or 2025 data. If it does, that data is contaminated forever per the master plan. Add an explicit assertion at the top: assert end_year <= 2023, "OOS data must be held out"

Tests in tests/backtest/test_walk_forward.py:
- Mock run_backtest to return pre-canned BacktestResults
- Verify the splits are correct (train years, test year)
- Verify the assertion catches end_year > 2023
- Verify metrics are computed for each fold
```

**Verify:**
```bash
uv run pytest tests/backtest -v
uv run jupyter nbconvert --to notebook --execute notebooks/05_walk_forward_validation.ipynb --output 05_walk_forward_validation_executed.ipynb
```

---

# Sprint 6 — Paper Trading

**Sprint goal:** Deploy the system to Alpaca paper trading. Run for 60 calendar days. Compare to backtest expectations.
**Duration:** Master plan: 8 weeks (60 days observation + 1 week build). Claude Code: 4–5 days build + 60 days observation.
**Cost gate:** Polygon Starter ($29/mo) continues. Alpaca paper is free.
**Execution decision:** This blueprint implements **Option A (Opening-range pullback)** from master plan v4 — free, IEX-compatible. If you've decided on Option B (true VWAP via Polygon), substitute the relevant ticket.
**Definition of done:** Paper Sharpe within ±0.5 of backtest expectation over 60 calendar days; no silent failures; you didn't tinker mid-window.

### Ticket 6.1 — Alpaca client wrapper

**Goal:** Thin Alpaca client for paper trading.
**Deliverable:** `src/execution/alpaca_client.py`, tests.

**Prompt:**
```
Add `uv add alpaca-py` to the project (the official current SDK; alpaca-trade-api is deprecated).

In src/execution/alpaca_client.py, wrap alpaca-py for paper trading.

Class AlpacaClient:
  - __init__ uses settings.alpaca_api_key, settings.alpaca_api_secret, settings.alpaca_base_url (paper URL by default)
  - get_account() -> dict  (cash, equity, buying_power)
  - get_positions() -> pd.DataFrame  (ticker, shares, avg_entry_price, current_price, unrealized_pnl)
  - get_open_orders() -> pd.DataFrame
  - get_minute_bars(ticker: str, start: datetime, end: datetime) -> pd.DataFrame
      Use IEX feed (free tier). Document this clearly in the docstring.
  - submit_limit_order(ticker, qty, side, limit_price, time_in_force="day") -> str  (order id)
  - submit_stop_order(ticker, qty, side, stop_price, time_in_force="gtc") -> str
  - cancel_order(order_id) -> None
  - get_first_30min_bars(ticker, trade_date) -> pd.DataFrame
      Returns 1-minute IEX bars from 9:30 AM to 10:00 AM on trade_date
      Computes high, low, open from the 30-min window

Tests in tests/execution/test_alpaca_client.py:
- Mock alpaca-py
- Verify each method calls the correct underlying SDK function
- Verify get_first_30min_bars returns a DataFrame even when trades are sparse (acknowledged IEX limitation)

Add a clear FIXME at the top noting that IEX is ~2-3% of volume and this is the documented Option A trade-off per master plan v4.

Stay in scope. No order logic yet.
```

**Verify:**
```bash
uv run pytest tests/execution/test_alpaca_client.py -v
# Smoke test (real paper API):
uv run python -c "
from src.execution.alpaca_client import AlpacaClient
c = AlpacaClient()
print(c.get_account())
"
```

### Ticket 6.2 — Daily candidate scanner job

**Goal:** Production-ready job that runs after market close, scores universe, identifies tomorrow's candidates.
**Deliverable:** `src/execution/daily_scan.py`, log output.

**Prompt:**
```
In src/execution/daily_scan.py, build the daily candidate scan job.

Function (and CLI entry point):
  def run_daily_scan(as_of_date: date | None = None) -> pd.DataFrame
    - as_of_date defaults to today
    - Steps:
      1. Check regime. If RED → log "REGIME RED — no scan" and return empty DataFrame
      2. Load yesterday's universe (Sprint 2 output)
      3. Refresh signal data for the last 30 days (incremental, not full pull):
         - actuals: any 8-K filings since last refresh
         - estimates: refresh ticker.earnings_history for tickers with recent earnings
         - revisions: incremental
         - insider: incremental
      4. Run master_alpha_score with as_of_date
      5. Apply select_candidates(top_n=8, min_score=0.70)
      6. Apply YELLOW regime sizing if regime is YELLOW (annotate the DataFrame)
      7. Save output to data/processed/scans/{as_of_date}.parquet
      8. Return the DataFrame

CLI: `python -m src.execution.daily_scan` runs for today.

Add to scripts/run_daily_scan.sh: a bash wrapper that activates the uv venv and calls the module, with all errors logged to data/logs/daily_scan_{date}.log.

Tests in tests/execution/test_daily_scan.py:
- Mock all the underlying signal modules
- Verify RED regime short-circuits
- Verify YELLOW annotates correctly
- Verify the saved output file path matches the date

Add a structured log line at the end of every run: ISO date, regime, n_candidates, runtime_seconds. This is what you'll grep when paper trading goes wrong.
```

**Verify:**
```bash
uv run pytest tests/execution/test_daily_scan.py -v
uv run python -m src.execution.daily_scan
ls -la data/processed/scans/
```

### Ticket 6.3 — Opening-range pullback executor

**Goal:** At 10:00 AM ET, place limit orders for today's candidates at the OR-pullback price.
**Deliverable:** `src/execution/morning_orders.py`.

**Prompt:**
```
In src/execution/morning_orders.py, implement the morning order placement per master plan v4 Option A (opening-range pullback).

Function:
  def place_morning_orders(scan_date: date, portfolio_value: float | None = None) -> list[dict]
    - Read candidates from data/processed/scans/{scan_date}.parquet
    - For each candidate ticker:
        1. Pull first-30-minute bars from Alpaca IEX (9:30-10:00 AM ET on today's date — note this runs AT 10:00 AM)
        2. Compute: open_price = first bar's open
                    or_low = min(low) over 30-min window
                    limit_price = (open_price + or_low) / 2
        3. Compute ATR_14 from yesterday and prior 13 days (use Polygon)
        4. Run position_size to determine shares
        5. Submit limit order via AlpacaClient with time_in_force="day" (auto-cancels at close)
           IMPORTANT: also schedule cancellation at 10:30 AM via APScheduler — see Ticket 6.5
        6. Log: ticker, limit_price, shares, ATR, order_id
    - Return list of order records

CLI entry point: `python -m src.execution.morning_orders` runs against today.

If portfolio_value is None, fetch it from AlpacaClient.get_account()['equity'].

Tests in tests/execution/test_morning_orders.py:
- Mock AlpacaClient and Polygon
- Verify the limit price formula
- Verify orders are tagged with the right time_in_force
- Verify the YELLOW regime case applies 50% sizing (read regime annotation from the scan parquet)

Add a clear top-of-file note: this is Option A from master plan v4. If migrating to Option B (true VWAP), the limit_price computation is the only thing that changes.
```

**Verify:**
```bash
uv run pytest tests/execution/test_morning_orders.py -v
```

### Ticket 6.4 — Stop placement and exit manager

**Goal:** After fills confirm, place GTC stops. Daily check for time-based exits and abnormal-gain partials.
**Deliverable:** `src/execution/exit_manager.py`.

**Prompt:**
```
In src/execution/exit_manager.py, implement post-fill stop placement and the exit manager.

Function:
  def place_stops_for_fills() -> None
    - Polls AlpacaClient for filled orders in the last 5 minutes
    - For each fill, computes stop_price = fill_price - 2.5 * ATR_14
    - Submits stop order via AlpacaClient with time_in_force="gtc"
    - Logs: ticker, fill_price, stop_price, atr, stop_order_id

Function:
  def manage_exits() -> None
    - Runs once per day (e.g., at 3:30 PM ET, 30 min before close)
    - For each open position:
        1. Check if days_held >= 15 → submit market-on-close sell
        2. Check if cumulative return >= 20% AND days_held <= 5 → submit market sell for 50% of shares (partial exit)
        3. Check regime: if regime turned RED → submit market sell for full position
    - Log every action

Persistence: positions need entry_date and entry_price for the time-exit and partial-exit logic. Don't trust Alpaca's "avg_entry_price" alone. Maintain a local SQLite (use sqlite3 stdlib) or parquet file at data/state/positions.parquet that tracks: ticker, entry_date, entry_price, shares, atr_at_entry, stop_price.

Tests in tests/execution/test_exit_manager.py:
- Fixture positions at various holding periods
- Verify day-15 exit fires
- Verify abnormal-gain partial fires correctly only within 5 days
- Verify regime RED triggers full liquidation
- Verify state persistence round-trips correctly

This is the highest-stakes module in Sprint 6 — a bug here costs real money in Phase 7. Test thoroughly.
```

**Verify:**
```bash
uv run pytest tests/execution/test_exit_manager.py -v
```

### Ticket 6.5 — Scheduler and runtime orchestration

**Goal:** APScheduler-based runtime that wires everything to the right times of day.
**Deliverable:** `src/execution/scheduler.py`, systemd service file or cron config.

**Prompt:**
```
In src/execution/scheduler.py, build the runtime scheduler using APScheduler (BlockingScheduler).

Add `uv add apscheduler pytz`.

The schedule (all times America/New_York timezone):
  - 18:00 (previous day) — run_daily_scan via daily_scan.py
  - 09:30 — sanity_check_market_open (verify market is open today, log)
  - 10:00 — place_morning_orders via morning_orders.py
  - 10:30 — cancel any unfilled morning orders
  - Continuously throughout day (every 30s, 9:35-16:00) — place_stops_for_fills (poll for fills)
  - 15:30 — manage_exits (time-based, partial, regime checks)
  - 16:30 — end_of_day_reconciliation: log P&L, position summary, write to data/logs/eod_{date}.json

Skip all jobs on US market holidays. Use pandas_market_calendars (uv add pandas-market-calendars) to check NYSE schedule.

Add comprehensive logging: every job logs start, end, and status. Add a heartbeat every 5 minutes during market hours so you can detect if the scheduler died.

Add a kill-switch: if any job raises an unhandled exception, log critical and EXIT. Don't keep running silently. Operator needs to be alerted.

CLI: `python -m src.execution.scheduler` starts the scheduler.

Then create scripts/install_systemd.sh that:
  - Generates a systemd unit file at /etc/systemd/system/swing-trader.service
  - The unit runs `uv run python -m src.execution.scheduler` as a service
  - Restart=on-failure with a 60s delay
  - Logs to journalctl

Alternative for non-Linux: scripts/run_scheduler.sh that runs the scheduler in a tmux session.

Tests in tests/execution/test_scheduler.py:
- Verify all jobs are registered with correct cron triggers
- Verify market holiday skip logic
- Verify the kill-switch behavior on exception (use mock to raise from a job)

This is the integration glue. If a piece is wrong here, the whole system silently fails to trade — exactly the failure mode we're guarding against. Test the holiday skip and the heartbeat in particular.
```

**Verify:**
```bash
uv run pytest tests/execution/test_scheduler.py -v
# Dry-run the scheduler for 5 minutes:
timeout 300 uv run python -m src.execution.scheduler || true
# Check log output for heartbeats and job registration messages.
```

### Ticket 6.6 — Monitoring dashboard and alerting

**Goal:** A simple status page and email/Pushover alerts for any abnormal condition.
**Deliverable:** `src/execution/monitoring.py`, `scripts/status.py`.

**Prompt:**
```
In src/execution/monitoring.py, implement monitoring and alerting.

Function:
  def daily_health_check() -> dict
    Checks:
    - Account equity vs yesterday: alert if intraday loss > 3%
    - Open positions count: alert if > max_positions
    - Stale price data: alert if any open position has not had a price update in 24h
    - Regime change: alert on every GREEN→YELLOW or YELLOW→RED transition
    - Scheduler heartbeat: alert if no heartbeat log in last 15 minutes during market hours
    - Backtest-vs-live drift: every Friday, compute rolling 30-day live Sharpe and compare to backtest expectation; alert if delta > 0.5

  Returns dict of: {check_name: {"status": "OK" | "WARN" | "CRITICAL", "message": str, "value": Any}}

Implement two alert channels:
  - Email via standard library smtplib (configure via env: ALERT_EMAIL_FROM, ALERT_EMAIL_TO, ALERT_SMTP_HOST, ALERT_SMTP_USER, ALERT_SMTP_PASS)
  - Pushover for mobile push (optional, configure via env: PUSHOVER_USER_KEY, PUSHOVER_API_TOKEN)
  Send CRITICAL via both channels, WARN via email only.

In scripts/status.py, build a simple CLI status report:
  uv run python scripts/status.py
  
  Prints to stdout:
  - Today's regime
  - Account equity, cash, buying power
  - Open positions table (ticker, shares, entry_price, current_price, unrealized_pnl, days_held)
  - Today's candidates (if scan has run)
  - Last 5 closed trades with P&L
  - Health check summary

Tests in tests/execution/test_monitoring.py:
- Mock alpaca, polygon, smtplib, pushover
- Verify each health check fires under the right conditions
- Verify alerts are sent through both channels for CRITICAL
- Verify backtest-vs-live drift calculation

Add the daily_health_check to the scheduler (Ticket 6.5): run at 16:35 ET every weekday.
```

**Verify:**
```bash
uv run pytest tests/execution/test_monitoring.py -v
uv run python scripts/status.py
```

### Ticket 6.7 — 60-day observation discipline

**Goal:** Lock the system. Define the observation protocol.
**Deliverable:** `OBSERVATION_PROTOCOL.md`, `scripts/end_of_observation.py`.

**Prompt:**
```
Create OBSERVATION_PROTOCOL.md at the project root.

Content:

# 60-Day Paper Trading Observation Protocol

Per master_plan_v4.md Phase 6, the observation window is 60 calendar days from <FILL DATE> to <FILL DATE + 60>.

## Rules during observation
1. NO code changes to src/signals, src/backtest, or src/execution unless required to fix a fatal bug (defined as: an exception that halts the scheduler).
2. Configuration changes (thresholds, weights, sizing) are FORBIDDEN.
3. Bug fixes that ARE allowed: API breakage handlers, retry logic, error logging improvements, monitoring fixes.
4. Any observed issue with strategy logic gets logged in OBSERVED_ISSUES.md and is addressed AFTER day 60, not during.

## Daily checklist (5 minutes)
- Check overnight log for errors
- Confirm scheduler heartbeat is current
- Run `python scripts/status.py`
- If any CRITICAL alert: investigate logs, fix only the operational issue, do not adjust strategy

## Weekly review (15 minutes, Sundays)
- Review the 7 daily logs for patterns
- Note any market events that may have impacted results (Fed days, surprise CPI, etc.) in OBSERVED_ISSUES.md
- Do not act on patterns yet — record only

## End-of-observation protocol (day 60)
- Run `uv run python scripts/end_of_observation.py`
- This computes:
  - Realized Sharpe over the 60-day window
  - Backtest's expected Sharpe for the same calendar window (run backtest engine on those 60 days using point-in-time-correct historical data)
  - Delta vs. expectation
  - Per-trade comparison: any trades the system took that the backtest would NOT have taken (and vice versa) — execution drift
- Master plan v4 PASS criteria:
  - Realized Sharpe within ±0.5 of backtest expectation
  - No silent failures (zero unhandled exceptions, zero missed trades)
  - You did not modify the strategy mid-window
- If PASS: proceed to Phase 7 capital deployment
- If FAIL: review OBSERVED_ISSUES.md, identify root cause, fix, restart 60-day observation from day 0. Do not skip the restart.

In scripts/end_of_observation.py, implement the analysis described above. The script should output a clear PASS/FAIL summary and save the analysis to data/reports/observation_{start_date}_to_{end_date}.html.

Tests in tests/scripts/test_end_of_observation.py:
- Mock backtest results and live results with controlled deltas
- Verify PASS when realized Sharpe is within ±0.5 of expected
- Verify FAIL when realized Sharpe deviates by more than 0.5
- Verify the report HTML is generated
```

**Verify:**
```bash
uv run pytest tests/scripts/test_end_of_observation.py -v
test -f OBSERVATION_PROTOCOL.md
```

---

# Sprint Summary

| Sprint | Master Plan Phase | Tickets | Time (Claude Code build) | Time (Calendar) |
|---|---|---|---|---|
| 0 | Bootstrap | 0.1, 0.2 | ~2 hours | 1 day |
| 1 | Phase 1 | 1.1, 1.2, 1.3 | ~6 hours | 1–2 days |
| 2 | Phase 2 | 2.1, 2.2, 2.3 | ~8 hours | 2–3 days |
| 3 | Phase 3 | 3.1, 3.2, 3.3, 3.4, 3.5 | ~14 hours | 3–4 days |
| 4 | Phase 4 | 4.1, 4.2, 4.3, 4.4 | ~10 hours | 2–3 days |
| 5 | Phase 5 | 5.1, 5.2, 5.3, 5.4, 5.5 | ~20 hours | 1–2 weeks |
| 6 | Phase 6 (build) | 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7 | ~16 hours | 4–5 days |
| 6 | Phase 6 (observation) | — | 0 hours | 60 calendar days |

**Total build time before live deployment:** ~76 hours of Claude Code work spread across ~22 calendar weeks (2 weeks of which are paper-trading observation that requires no coding).

# Operating principles for working with Claude Code

1. **Trust but verify.** Read the diff before accepting. Claude Code can hallucinate types, miss edge cases, or invent function signatures from libraries. The `Verify` block exists for this reason — run it after every ticket.
2. **One ticket per session.** Use `/clear` between tickets to keep context lean and behavior predictable.
3. **`CLAUDE.md` is your friend.** It's the standing instructions Claude Code reads at session start. If you find yourself repeating "use type hints" in every prompt, add it to `CLAUDE.md` instead.
4. **Reference the master plan.** When ambiguity arises, the prompts here say "per master_plan_v4.md Phase X." Keep that file in the project root so Claude Code can read it.
5. **Don't let it skip tests.** A common Claude Code failure mode is to write the implementation, then write tests that pass trivially. The Verify block runs the tests against the actual code — if they pass too easily, inspect them.
6. **Cost the long-running stuff.** Backtests and walk-forward will eat tokens if you let Claude Code generate them line-by-line. Run them outside the Claude Code session: `uv run python -m src.backtest.walk_forward` from your shell, then paste the result back if you want analysis.

# When you finish a ticket

```bash
# Run the full test suite (catches regressions in earlier modules)
uv run pytest

# Lint and type-check
uv run ruff check . --fix
uv run mypy src

# Commit
git add -A
git commit -m "ticket X.Y: <one-line description>"
```

If `pytest` shows failures in tickets you previously closed, that's a regression. Roll back, isolate, fix in a separate prompt.

# When the master plan is wrong

It will happen. Real implementation reveals assumptions the design didn't catch. The protocol:

1. Stop coding.
2. Document the issue in `MASTER_PLAN_DELTAS.md` at the project root: what the plan said, what implementation requires, why.
3. Decide: is this a "bug in the plan" (rewrite the plan first, then come back) or a "tactical adjustment that doesn't change the trading logic" (record it and proceed)?
4. Never silently diverge. Every deviation gets a paper trail.

The master plan is locked, not infallible. Locked means: no changes without explicit human review.
