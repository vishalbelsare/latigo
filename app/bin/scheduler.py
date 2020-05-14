#!/usr/bin/env python

import os
import socket
import sys
import threading

from latigo import __version__ as latigo_version
from latigo.log import add_azure_logging, setup_logging
from latigo.scheduler import Scheduler
from latigo.utils import get_nested_config_value, load_configs

logger = setup_logging(__name__)


config, err = load_configs("../../deploy/scheduler_config.yaml", os.environ["LATIGO_SCHEDULER_CONFIG_FILE"] or None,)
if not config:
    # try to load config in another folder  # TODO remove this after repo will be reformatted from "library" way
    config, err = load_configs("../../deploy/scheduler_config.yaml", os.environ["LATIGO_SCHEDULER_CONFIG_FILE"] or None)

if not config:
    logger.error(f"Could not load configuration for scheduler: {err}")
    sys.exit(1)

threading.current_thread().name = config.get("scheduler", {}).get(
    "instance_name", f"latigo-scheduler-{latigo_version}-{socket.getfqdn()}"
)
add_azure_logging(
    get_nested_config_value(config, "scheduler", "azure_monitor_logging_enabled"),
    get_nested_config_value(config, "scheduler", "azure_monitor_instrumentation_key"),
)

logger.info("Configuring Latigo Scheduler")
scheduler = Scheduler(config)
scheduler.print_summary()
logger.info("Running Latigo Scheduler")
scheduler.run()
logger.info("Stopping Latigo Scheduler")
