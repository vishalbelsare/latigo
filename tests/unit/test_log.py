"""Tests for logging functionality."""
import logging
from typing import Optional
from unittest.mock import patch, sentinel, Mock

import pytest

from latigo.log import measure
from latigo.log.measurement import MeasurementContextManager


@pytest.fixture
def patch_time():
    with patch("latigo.log.measurement.monotonic", return_value=0) as mock_time:
        with patch(
            "latigo.log.measurement.MeasurementContextManager",
            side_effect=lambda *a, **kw: MeasurementContextManager(*a, start_time=mock_time(), **kw),
        ):
            yield mock_time


@pytest.fixture
def advance(patch_time, caplog):
    """Move patched clock forward, execute a callback if one provided.

    Also provide some useful updates for log records.
    """

    def do_adwance(time: float, callback: Optional[callable] = None):
        # Copy context since it is updated between calls.
        for record in caplog.records:
            if hasattr(record, "context"):
                record.context = record.context.copy()

        patch_time.return_value += time
        if callback:
            return callback()

    return do_adwance


def test_measure_decorator(advance, caplog):
    # Create decorator, wrap the function and call it.
    result = measure("test_measure")(advance)(123.45, lambda: sentinel.return_value)
    assert result == sentinel.return_value
    assert caplog.record_tuples == [("latigo.log.measurement", logging.INFO, "Measured operation finished.")]
    assert caplog.records[0].context == {"delta": 123.45, "operation_id": "test_measure"}


def test_measure_decorator_call_twice(advance, caplog):
    decorated_func = measure("test_measure")(advance)

    decorated_func(100)
    decorated_func(50)

    assert caplog.record_tuples == [
        ("latigo.log.measurement", logging.INFO, "Measured operation finished."),
        ("latigo.log.measurement", logging.INFO, "Measured operation finished."),
    ]

    contexts = [r.context for r in caplog.records]
    assert contexts == [{"delta": 100, "operation_id": "test_measure"}, {"delta": 50, "operation_id": "test_measure"}]


def test_measure_decorator_fails(advance, caplog):
    # Create decorator, wrap the function and call it.
    with pytest.raises(KeyError, match=r":-\)"):
        measure("test_measure")(advance)(123.45, Mock(side_effect=KeyError(":-)")))

    assert caplog.record_tuples == [("latigo.log.measurement", logging.INFO, "Measured operation failed.")]
    assert caplog.records[0].context == {"delta": 123.45, "operation_id": "test_measure"}


def test_measure_context_manager(advance, caplog):
    with measure("test_measure"):
        advance(123.45)

    assert caplog.record_tuples == [("latigo.log.measurement", logging.INFO, "Measured operation finished.")]
    assert caplog.records[0].context == {"delta": 123.45, "operation_id": "test_measure"}


def test_measure_round_delta(advance, caplog):
    with measure("test_measure"):
        advance(123.4567890)

    assert caplog.record_tuples == [("latigo.log.measurement", logging.INFO, "Measured operation finished.")]
    assert caplog.records[0].context == {"delta": 123.457, "operation_id": "test_measure"}


def test_measure_context_manager_failure(advance, caplog):
    with pytest.raises(RuntimeError), measure("test_measure"):
        advance(123.45)
        raise RuntimeError

    assert caplog.record_tuples == [("latigo.log.measurement", logging.INFO, "Measured operation failed.")]
    assert caplog.records[0].context == {"delta": 123.45, "operation_id": "test_measure"}


def test_measure_custom_logger(advance, caplog):
    with measure("test_measure", logger=logging.getLogger("latigo.test-logger")):
        advance(123.45)

    assert caplog.record_tuples == [("latigo.test-logger", logging.INFO, "Measured operation finished.")]
    assert caplog.records[0].context == {"delta": 123.45, "operation_id": "test_measure"}


def test_measure_custom_level(advance, caplog):
    caplog.set_level(logging.DEBUG)
    with measure("test_measure", level=logging.DEBUG):
        advance(123.45)

    assert caplog.record_tuples == [("latigo.log.measurement", logging.DEBUG, "Measured operation finished.")]
    assert caplog.records[0].context == {"delta": 123.45, "operation_id": "test_measure"}


def test_measure_two_functions(advance, caplog):
    with measure("test_measure"):
        advance(123.45)
        logging.info("Intermediate log.")
        advance(67.89)

    assert caplog.record_tuples == [
        ("root", logging.INFO, "Intermediate log."),
        ("latigo.log.measurement", logging.INFO, "Measured operation finished."),
    ]

    intermediate_record, teardown_record = caplog.records

    assert teardown_record.context == {"delta": 191.34, "operation_id": "test_measure"}
    assert not hasattr(intermediate_record, "context")
