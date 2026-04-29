import pytest
from pydantic import ValidationError

from src.config.settings import Settings, get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_settings_loads_required_fields(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "test-fred-key")
    monkeypatch.setenv("SEC_EDGAR_USER_AGENT", "MyApp/1.0 admin@example.com")

    settings = Settings(_env_file=None)

    assert settings.fred_api_key == "test-fred-key"
    assert settings.sec_edgar_user_agent == "MyApp/1.0 admin@example.com"


def test_settings_optional_fields_default_to_none(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "test-fred-key")
    monkeypatch.setenv("SEC_EDGAR_USER_AGENT", "test-agent")

    settings = Settings(_env_file=None)

    assert settings.polygon_api_key is None
    assert settings.alpaca_api_key is None
    assert settings.alpaca_api_secret is None


def test_settings_default_alpaca_base_url(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "test-fred-key")
    monkeypatch.setenv("SEC_EDGAR_USER_AGENT", "test-agent")

    settings = Settings(_env_file=None)

    assert settings.alpaca_base_url == "https://paper-api.alpaca.markets"


def test_settings_all_fields_set(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "fred-key")
    monkeypatch.setenv("SEC_EDGAR_USER_AGENT", "test-agent")
    monkeypatch.setenv("POLYGON_API_KEY", "poly-key")
    monkeypatch.setenv("ALPACA_API_KEY", "alpaca-key")
    monkeypatch.setenv("ALPACA_API_SECRET", "alpaca-secret")
    monkeypatch.setenv("ALPACA_BASE_URL", "https://api.alpaca.markets")

    settings = Settings(_env_file=None)

    assert settings.polygon_api_key == "poly-key"
    assert settings.alpaca_api_key == "alpaca-key"
    assert settings.alpaca_api_secret == "alpaca-secret"
    assert settings.alpaca_base_url == "https://api.alpaca.markets"


def test_settings_missing_fred_api_key_raises(monkeypatch):
    # env_ignore_empty=True means an empty value in .env is also treated as missing
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    monkeypatch.setenv("SEC_EDGAR_USER_AGENT", "test-agent")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_missing_sec_edgar_user_agent_raises(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "test-key")
    monkeypatch.delenv("SEC_EDGAR_USER_AGENT", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_get_settings_returns_cached_instance(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "test-key")
    monkeypatch.setenv("SEC_EDGAR_USER_AGENT", "test-agent")

    s1 = get_settings()
    s2 = get_settings()

    assert s1 is s2
