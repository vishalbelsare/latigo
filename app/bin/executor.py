#!/usr/bin/env python

import copy
import logging
import os
from functools import partial
from pathlib import Path

import sys

from latigo.executor import PredictionExecutor
from latigo.log import setup_logging
from latigo.utils import load_configs, get_nested_config_value

logger = logging.getLogger("latigo")
NAME = "executor"
DEFAULT_CONFIG_PATHS = Path(__file__).parent.parent.parent / "deploy" / "executor_config.yaml"
BASE_CONFIG_PATH = os.environ.get("LATIGO_EXECUTOR_CONFIG_FILE")

if __name__ == "__main__":
    config, err = load_configs(DEFAULT_CONFIG_PATHS, BASE_CONFIG_PATH)
    get_config = partial(get_nested_config_value, config, NAME)

    # Ensure logging is configured even if there is no config.
    setup_logging(
        f"latigo-{ NAME }",
        enable_azure_logging=get_config("azure_monitor_logging_enabled"),
        azure_monitor_instrumentation_key=get_config("azure_monitor_instrumentation_key"),
        log_debug_enabled=get_config("log_debug_enabled"),
    )

    if not config:
        logger.error(f"Could not load configuration for %s: %r", NAME, err)
        sys.exit(1)

    executor = PredictionExecutor(config=copy.deepcopy(config))
    executor.print_summary()
    executor.run()
