#!/usr/bin/env python

import copy
import os
import socket
import sys
import threading

from latigo import __version__ as latigo_version
from latigo.executor import PredictionExecutor
from latigo.log import add_azure_logging, setup_logging
from latigo.utils import get_nested_config_value, load_configs

logger = setup_logging(__name__)


config, err = load_configs("../deploy/executor_config.yaml", os.environ["LATIGO_EXECUTOR_CONFIG_FILE"] or None)
if not config:
    # try to load config in another folder  # TODO remove this after repo will be reformatted from "library" way
    config, err = load_configs("../../deploy/executor_config.yaml", os.environ["LATIGO_EXECUTOR_CONFIG_FILE"] or None)

if not config:
    logger.error(f"Could not load configuration for executor: {err}")
    sys.exit(1)

instance_name = config.get("executor", {}).get("instance_name", f"latigo-executor-{latigo_version}-{socket.getfqdn()}")
threading.current_thread().name = instance_name
add_azure_logging(
    get_nested_config_value(config, "executor", "azure_monitor_logging_enabled"),
    get_nested_config_value(config, "executor", "azure_monitor_instrumentation_key"),
)


if __name__ == "__main__":
    executor = PredictionExecutor(config=copy.deepcopy(config))
    executor.print_summary()
    executor.run()
