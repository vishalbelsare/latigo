"""Common configuration for application startup."""
import logging
import os
from functools import partial
from pathlib import Path

import sys

from latigo.log import setup_logging
from latigo.utils import load_configs, get_nested_config_value

logger = logging.getLogger("latigo")
CONFIG_DIR_PATH = Path(__file__).parent.parent.parent / "deploy"
if not CONFIG_DIR_PATH.exists():
    # Directory structure in Docker differs from current directory structure
    CONFIG_DIR_PATH = Path("/app/deploy")


def basic_config(name):
    """Load configuration and setup logs."""
    default_config_path = CONFIG_DIR_PATH / f"{ name }_config.yaml"
    base_config_path = os.environ.get(f"LATIGO_{ name.upper() }_CONFIG_FILE")

    config, err = load_configs(default_config_path, base_config_path)
    get_config = partial(get_nested_config_value, config, name)

    # Ensure logging is configured even if there is no config.
    setup_logging(
        f"latigo-{ name }",
        enable_azure_logging=get_config("azure_monitor_logging_enabled"),
        azure_monitor_instrumentation_key=get_config("azure_monitor_instrumentation_key"),
        log_debug_enabled=get_config("log_debug_enabled"),
    )

    if not config:
        logger.error(f"Could not load configuration for %s: %r", name, err)
        sys.exit(1)

    return config
