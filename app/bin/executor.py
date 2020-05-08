#!/usr/bin/env python

import sys
import pprint
import multiprocessing
import threading
import socket
import copy
import distutils.util
import os
import typing
from latigo.log import setup_logging
from latigo.log import add_azure_logging
from latigo import __version__ as latigo_version

logger = setup_logging("latigo.app.executor")

import multiprocessing_logging

multiprocessing_logging.install_mp_handler()

from latigo.utils import load_configs, sleep, get_nested_config_value
from latigo.executor import PredictionExecutor

config, err = load_configs(
    "../deploy/executor_config.yaml", os.environ["LATIGO_EXECUTOR_CONFIG_FILE"] or None
)
if not config:
    logger.error(f"Could not load configuration for executor: {err}")
    sleep(60 * 5)
    sys.exit(1)

instance_count = int(config.get("executor", {}).get("instance_count", 1))
instance_name = config.get("executor", {}).get(
    "instance_name", f"latigo-executor-{latigo_version}-{socket.getfqdn()}"
)
threading.current_thread().name = instance_name
add_azure_logging(
    logger,
    get_nested_config_value(config, "executor", "azure_monitor_logging_enabled"),
    get_nested_config_value(config, "executor", "azure_monitor_instrumentation_key")
)


def wrap_executor(executor):
    executor.run()


if __name__ == "__main__":
    instances = []
    first: bool = True
    for instance_index in range(instance_count):
        # logger.info(f"Configuring Latigo Executor {instance_index+1}/{instance_count}")
        # process = multiprocessing.Process(target=wrap_executor, args=(config,))
        executor = PredictionExecutor(config=copy.deepcopy(config))
        if first:
            first = False
            executor.print_summary()
        process = threading.Thread(
            target=wrap_executor,
            name=f"{instance_name}-thread-{instance_index+1}",
            args=(executor,),
        )
        instances.append(process)
    logger.info(f"Configured {instance_index+1}/{instance_count} Latigo Executor(s)")
    for instance_index in range(instance_count):
        # logger.info(f"Running Latigo Executor {instance_index+1}/{instance_count}")
        # Allow scheduler to have a head start and stagger startup
        sleep(5 / instance_count)
        process = instances[instance_index]
        process.start()
    logger.info(f"Started {instance_index+1}/{instance_count} Latigo Executor(s)")
    for instance_index in range(instance_count):
        executor = instances[instance_index]
        process = instances[instance_index]
        process.join()
        # logger.info(f"Latigo Executor {instance_index+1}/{instance_count} stopped")
    logger.info(f"Stopped {instance_index+1}/{instance_count} Latigo Executor(s)")
