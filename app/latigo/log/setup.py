import logging
import os
import socket
from logging.config import dictConfig

import latigo

import pylogctx
from colorlog import ColoredFormatter
from opencensus.ext.azure.log_exporter import AzureLogHandler

__all__ = ["setup_logging"]

LOGS_TO_SUPPRESS = (
    "requests",
    "tensorboard",
    "urllib3",
    "aiohttp.access",
    "uamqp",
    "adal-python",
    "matplotlib.font_manager",
    "gordo",
)
logger = logging.getLogger(__name__)


class LatigoFormatter(ColoredFormatter):
    """Formatter that adds extra logging info."""

    def format(self, record):
        """Add extra context to the record."""
        context = getattr(record, "context", {})

        if record.exc_info:
            context["exception"] = record.exc_info[0].__name__

        context.update(pylogctx.context.as_dict())

        if context:
            context_str = ", ".join(f"{ k }:{ v }" for k, v in context.items())
            record.msg = f"{ record.msg } ({ context_str })"

        return super().format(record)


def setup_logging(name, *, enable_azure_logging=False, azure_monitor_instrumentation_key=None):
    """Set up the logging."""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    process_info = f"{ name }-{ latigo.__version__ }-{ socket.getfqdn() }"

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
        "loggers": {"latigo": {"level": log_level}, **{k: {"level": "WARNING"} for k in LOGS_TO_SUPPRESS}},
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
