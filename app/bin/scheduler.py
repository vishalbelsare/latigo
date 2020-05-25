#!/usr/bin/env python
import logging
import os
from pathlib import Path

import sys

from latigo.log import setup_logging
from latigo.scheduler import Scheduler
from latigo.utils import load_configs, get_nested_config_value

logger = logging.getLogger("latigo")
DEFAULT_CONFIG_PATHS = Path(__file__).parent.parent.parent / "deploy" / "scheduler_config.yaml"
BASE_CONFIG_PATH = os.environ.get("LATIGO_SCHEDULER_CONFIG_FILE")


if __name__ == "__main__":
    config, err = load_configs(DEFAULT_CONFIG_PATHS, BASE_CONFIG_PATH)

    # Ensure logging is configured even if there is no config.
    setup_logging(
        "latigo-scheduler",
        enable_azure_logging=get_nested_config_value(config, "scheduler", "azure_monitor_logging_enabled"),
        azure_monitor_instrumentation_key=get_nested_config_value(
            config, "scheduler", "azure_monitor_instrumentation_key"
        ),
    )

    if not config:
        logger.error(f"Could not load configuration for executor: {err}")
        sys.exit(1)

    logger.info("Configuring Latigo Scheduler")
    scheduler = Scheduler(config)
    scheduler.print_summary()
    logger.info("Running Latigo Scheduler")
    scheduler.run()
    logger.info("Stopping Latigo Scheduler")
