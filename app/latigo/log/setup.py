import logging
import os
import socket
import traceback
from logging.config import dictConfig
from pathlib import Path

import latigo

import pylogctx
from colorlog import ColoredFormatter
from opencensus.ext.azure.log_exporter import AzureLogHandler

__all__ = ["setup_logging"]

LOGS_TO_SUPPRESS = (
    "adal-python",
    "aiohttp.access",
    "gordo",
    "matplotlib.font_manager",
    "opencensus.ext.azure.common.transport",
    "requests",
    "tensorboard",
    "uamqp",
    "urllib3",
)
DEBUG_LOGGERS = ("latigo.log.measurement",)
ROOT = Path(__file__).parent.parent.parent.parent
TRACEBACK_ANALYSE_LIMIT = 20
logger = logging.getLogger(__name__)


class LatigoFormatter(ColoredFormatter):
    """Formatter that adds extra logging info."""

    def format(self, record):
        """Add extra context to the record."""
        context = getattr(record, "context", {})

        if record.exc_info:
            exc_type, exc_value, exc_tb = record.exc_info
            context.update({"exc_type": exc_type.__name__, "exc_val": exc_value, **self._extract_exc_location(exc_tb)})

        context.update(pylogctx.context.as_dict())

        if context:
            context_str = ", ".join(f"{ k }:{ v }" for k, v in context.items())
            record.msg = f"{ record.msg } ({ context_str })"

        return super().format(record)

    @staticmethod
    def _extract_exc_location(exc_tb):
        """Lookup traceback for the lowest line of Latigo source code.

        Provide extra context if a line is found within the limit.
        """
        local_code_frame = None
        local_code_path = None

        for frame in traceback.extract_tb(exc_tb, limit=TRACEBACK_ANALYSE_LIMIT):
            frame_path = Path(frame.filename)
            if ROOT not in frame_path.parents:
                break
            local_code_frame, local_code_path = frame, frame_path

        if not local_code_frame:
            return {}

        module = local_code_path.relative_to(ROOT)
        return {
            "location": ".".join(module.parts[:-1] + (module.stem, local_code_frame.name)),
            "line": repr(local_code_frame.line),
        }


def setup_logging(name, *, enable_azure_logging=False, azure_monitor_instrumentation_key=None, log_debug_enabled=False):
    """Set up the logging."""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    process_info = f"{ name }-{ latigo.__version__ }-{ socket.getfqdn() }"
    logs_to_suppress = LOGS_TO_SUPPRESS if log_debug_enabled else LOGS_TO_SUPPRESS + DEBUG_LOGGERS

    config = {
        "version": 1,
        "disable_existing_loggers": True,
        "formatters": {
            "default": {
                "()": LatigoFormatter,
                "fmt": f"%(log_color)s %(asctime)s %(levelname)s ({ process_info }) [%(name)s] %(message)s %(reset)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
                "log_colors": {
                    "DEBUG": "cyan",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "red",
                },
            }
        },
        "handlers": {"default": {"class": "logging.StreamHandler", "level": log_level, "formatter": "default"}},
        "loggers": {"latigo": {"level": log_level}, **{k: {"level": "WARNING"} for k in logs_to_suppress}},
        "root": {"level": log_level, "handlers": ["default"]},
    }

    if enable_azure_logging:
        if not azure_monitor_instrumentation_key:
            raise ValueError("'azure_monitor_instrumentation_key' can not be empty if Azure logging is enabled")

        config["handlers"]["azure_monitor"] = {
            "()": AzureLogHandler,
            "connection_string": f"InstrumentationKey={ azure_monitor_instrumentation_key }",
        }
        config["root"]["handlers"].append("azure_monitor")

    dictConfig(config)

    if enable_azure_logging:
        logger.info("AzureLogHandler was enabled.")
    else:
        logger.info("Logs are configured without AzureLogHandler")
