#!/usr/bin/env python

import sys
import pprint
import multiprocessing
import threading
import socket
import copy
import os
from latigo.log import setup_logging

logger = setup_logging("latigo.app.executor")

import multiprocessing_logging

multiprocessing_logging.install_mp_handler()

from latigo.utils import load_config, sleep
from latigo.executor import PredictionExecutor

# Augment loaded config with variables from environment
# fmt: off
# NOTE: REMEMBER TO UPDATE DOCKER FILES AS WELL TO PRORPERLY PROPEGATE VALUES
not_found=None #"environemnt variable not found"
config_overlay = {
    "executor": {
        "instance_count": os.environ.get("LATIGO_EXECUTOR_INSTANCE_COUNT", not_found),
        "instance_name": os.environ.get("LATIGO_INSTANCE_NAME", not_found),
    },
    "task_queue": {
        "connection_string": os.environ.get("LATIGO_INTERNAL_EVENT_HUB", not_found),
    },
    "model_info":{
        "connection_string": os.environ.get("LATIGO_GORDO_CONNECTION_STRING", not_found),
        "auth":{
            "resource": os.environ.get("LATIGO_GORDO_RESOURCE", not_found),
            "tenant" : os.environ.get("LATIGO_GORDO_TENANT", not_found),
            "authority_host_url" : os.environ.get("LATIGO_GORDO_AUTH_HOST_URL", not_found),
            "client_id" : os.environ.get("LATIGO_GORDO_CLIENT_ID", not_found),
            "client_secret" : os.environ.get("LATIGO_GORDO_CLIENT_SECRET", not_found),
        },
    },
    "sensor_data": {
        "base_url": os.environ.get("LATIGO_TIME_SERIES_BASE_URL", not_found),
        "auth":{
            "resource": os.environ.get("LATIGO_TIME_SERIES_RESOURCE", not_found),
            "tenant" : os.environ.get("LATIGO_TIME_SERIES_TENANT", not_found),
            "authority_host_url" : os.environ.get("LATIGO_TIME_SERIES_AUTH_HOST_URL", not_found),
            "client_id" : os.environ.get("LATIGO_TIME_SERIES_CLIENT_ID", not_found),
            "client_secret" : os.environ.get("LATIGO_TIME_SERIES_CLIENT_SECRET", not_found),
        },
    },
    "prediction_storage": {
        "base_url": os.environ.get("LATIGO_TIME_SERIES_BASE_URL", not_found),
        "auth":{
            "resource": os.environ.get("LATIGO_TIME_SERIES_RESOURCE", not_found),
            "tenant" : os.environ.get("LATIGO_TIME_SERIES_TENANT", not_found),
            "authority_host_url" : os.environ.get("LATIGO_TIME_SERIES_AUTH_HOST_URL", not_found),
            "client_id" : os.environ.get("LATIGO_TIME_SERIES_CLIENT_ID", not_found),
            "client_secret" : os.environ.get("LATIGO_TIME_SERIES_CLIENT_SECRET", not_found),
        },
    },
    "predictor": {
        "connection_string": os.environ.get("LATIGO_GORDO_CONNECTION_STRING", not_found),
        "auth":{
            "resource": os.environ.get("LATIGO_GORDO_RESOURCE", not_found),
            "tenant" : os.environ.get("LATIGO_GORDO_TENANT", not_found),
            "authority_host_url" : os.environ.get("LATIGO_GORDO_AUTH_HOST_URL", not_found),
            "client_id" : os.environ.get("LATIGO_GORDO_CLIENT_ID", not_found),
            "client_secret" : os.environ.get("LATIGO_GORDO_CLIENT_SECRET", not_found),
        },
    },
}
# fmt: on

config_filename = os.environ.get("LATIGO_EXECUTOR_CONFIG_FILE", "executor_config.yaml")
config = load_config(config_filename, config_overlay)
if not config:
    logger.error(f"Could not load configuration for executor from {config_filename}")
    sys.exit(1)


instance_count = int(config.get("executor", {}).get("instance_count", 1))
instance_name = config.get("executor", {}).get(
    "instance_name", "latigo-executor-" + socket.getfqdn()
)
threading.current_thread().name = instance_name


def wrap_executor(executor):
    executor.run()


if __name__ == "__main__":
    instances = []

    for instance_index in range(instance_count):
        # logger.info(f"Configuring Latigo Executor {instance_index+1}/{instance_count}")
        # process = multiprocessing.Process(target=wrap_executor, args=(config,))
        executor = PredictionExecutor(config=copy.deepcopy(config))
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
