# swing-trader

Systematic swing trading system. Python 3.11, managed with [uv](https://docs.astral.sh/uv/).

## Setup

```bash
uv sync
cp .env.example .env  # then fill in keys
```

## Common commands

```bash
uv run pytest          # run tests
uv run ruff check .    # lint
uv run mypy src        # type-check
```

## Layout

```
src/
  config/      # config loading, .env handling
  regime/      # Sprint 1
  universe/    # Sprint 2
  signals/     # Sprints 3, 4
  backtest/    # Sprint 5
  execution/   # Sprint 6
  common/      # logging, types, utilities
tests/         # mirror of src/
notebooks/     # exploratory Jupyter only
data/          # raw/ and processed/ (gitignored)
scripts/       # one-off CLI scripts
```

See `master_plan_v4.md` for the trading-logic source of truth and `CLAUDE.md` for
standing instructions for Claude Code sessions.
