# Standing instructions for Claude Code sessions

These rules apply to every session working in this repository.

## Source of truth
- `master_plan_v4.md` is the source of truth for trading logic. Never override it. If a request conflicts with the plan, surface the conflict and ask before proceeding.

## Language and typing
- Python 3.11. Use type hints everywhere.
- Use Python 3.11 syntax: `list[str]`, `dict[str, int]`, `X | None` (no `List`, `Dict`, `Optional` from `typing`).

## Testing
- Every public function gets a pytest test in the mirrored `tests/` path (e.g. `src/regime/foo.py` → `tests/regime/test_foo.py`).
- Mock all external APIs in tests. Never hit live FRED / EDGAR / Polygon / Alpaca from pytest.

## Data
- Use pandas with explicit dtypes. Never store dates as strings — use `datetime64`/`pd.Timestamp`.
- Use parquet (not CSV) for any DataFrame written to disk.

## Logging and output
- Use the standard `logging` module with one logger per module: `logger = logging.getLogger(__name__)`.
- No `print()` statements outside of CLI scripts in `scripts/`.

## Configuration and secrets
- All API keys come from environment variables loaded via `src/config`. Never hardcode keys.
- `.env` is gitignored; `.env.example` is the committed template.

## Dependencies
- Add dependencies with `uv add` (not `pip install`).
- Add dev-only dependencies with `uv add --dev`.

## Scope discipline
- Stay strictly within the scope of the current ticket. Do not refactor unrelated code.
- If a requirement is ambiguous, ask one clarifying question rather than guessing.
