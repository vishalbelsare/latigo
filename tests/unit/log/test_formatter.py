import logging
from pathlib import Path
from typing import Optional
from unittest.mock import sentinel, patch

import pylogctx
import sys

from latigo.log.setup import LatigoFormatter


def get_record(
    *,
    name="latigo.test-logger",
    level=logging.INFO,
    pathname=sentinel.pathname,
    lineno=42,
    msg="Test message",
    args=(),
    exc_info=None,
    extra=None,
):
    """Build a log record instance."""
    record = logging.LogRecord(
        name=name, level=level, pathname=pathname, lineno=lineno, msg=msg, args=args, exc_info=exc_info
    )
    if extra:
        # Update the record as typical logger does
        record.__dict__.update(extra)
    return record


def get_formatted_message(record: Optional[logging.LogRecord] = None):
    """Format a log record, stripping coloring characters."""
    if record is None:
        record = get_record()
    return LatigoFormatter().format(record)[5:-4]


def test_smoke():
    assert get_formatted_message() == "INFO:latigo.test-logger:Test message"


def test_explicitly_passed_context():
    record = get_record(extra={"context": {"x": sentinel.x, "y": sentinel.y}})
    assert get_formatted_message(record) == "INFO:latigo.test-logger:Test message (x:sentinel.x, y:sentinel.y)"


def test_pylogctx_context():
    with pylogctx.context(x=sentinel.x, y=sentinel.y):
        assert get_formatted_message() == "INFO:latigo.test-logger:Test message (x:sentinel.x, y:sentinel.y)"


def test_error_with_traceback():
    try:
        raise TypeError("To be handled by a test")
    except TypeError:
        record = get_record(exc_info=sys.exc_info())

    message = get_formatted_message(record)
    first_line = message.splitlines()[0]
    assert (
        first_line
        == """\
INFO:latigo.test-logger:Test message \
(exc_type:TypeError, \
exc_val:To be handled by a test, \
location:tests.unit.log.test_formatter.test_error_with_traceback, \
line:'raise TypeError("To be handled by a test")')"""
    )


def test_error_outside_source_code():
    try:
        raise TypeError("To be handled by a test")
    except TypeError:
        record = get_record(exc_info=sys.exc_info())

    with patch("latigo.log.setup.ROOT", new=Path("/hopefully-missing")):
        message = get_formatted_message(record)

    first_line = message.splitlines()[0]
    assert first_line == "INFO:latigo.test-logger:Test message (exc_type:TypeError, exc_val:To be handled by a test)"
