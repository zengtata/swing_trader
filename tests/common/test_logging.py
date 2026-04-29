import logging

import pytest

from src.common.logging import setup_logging


@pytest.fixture(autouse=True)
def reset_root_logger():
    root = logging.getLogger()
    original_level = root.level
    original_handlers = root.handlers[:]
    yield
    root.setLevel(original_level)
    root.handlers = original_handlers


def test_setup_logging_adds_stream_handler():
    root = logging.getLogger()
    before = len(root.handlers)

    setup_logging()

    assert len(root.handlers) == before + 1
    assert isinstance(root.handlers[-1], logging.StreamHandler)


def test_setup_logging_default_level_is_info():
    setup_logging()

    assert logging.getLogger().level == logging.INFO


def test_setup_logging_custom_level():
    setup_logging(level="DEBUG")

    assert logging.getLogger().level == logging.DEBUG


def test_setup_logging_captures_records(caplog):
    setup_logging()

    with caplog.at_level(logging.INFO, logger="test.module"):
        logging.getLogger("test.module").info("hello world")

    assert len(caplog.records) > 0
    assert caplog.records[0].message == "hello world"
    assert caplog.records[0].name == "test.module"
