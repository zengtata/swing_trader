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
