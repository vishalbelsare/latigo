"""Measurement tools for logging."""
import logging
from functools import wraps
from typing import Dict, Any

import attr
from time import monotonic

__all__ = ["measure"]

default_logger = logging.getLogger(__name__)


@attr.s(auto_attribs=True, slots=True)
class MeasurementContextManager:
    _context: Dict[str, Any]
    _logger: logging.Logger = default_logger
    _level: int = logging.INFO
    _start_time: float = attr.Factory(monotonic)

    def __enter__(self):
        self._logger.log(self._level, "Starting measurement.", extra={"context": self._context})
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._context["delta"] = monotonic() - self._start_time
        status = "failed" if exc_type else "finished"
        self._logger.log(self._level, "Measured operation %s.", status, extra={"context": self._context})

    def __call__(self, func):
        @wraps(func)
        def inner(*args, **kwargs):
            with attr.evolve(self, context={"operation_id": self._context["operation_id"]}, start_time=monotonic()):
                return func(*args, **kwargs)
        return inner


def measure(operation_id: str, *, logger=default_logger, level=logging.INFO):
    """Decorator and context manager for measuring execution time.

    Args:
        operation_id: human-readable string to identity the operation
            being measured.
        logger: logger instance to log measurement results.  If not
            provided, use default one.
        level: log level of the measurement result.
    """

    return MeasurementContextManager({"operation_id": operation_id}, logger=logger, level=level)
