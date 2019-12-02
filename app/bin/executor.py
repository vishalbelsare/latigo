#!/usr/bin/env python

import sys
import pprint
from os import environ
from latigo.log import setup_logging

logger = setup_logging("latigo.app.executor")
from latigo.utils import load_config
from latigo.executor import PredictionExecutor


logger.info(f"Starting Latigo Executor")

# Augment loaded config with variables from environment
# fmt: off
# NOTE: REMEMBER TO UPDATE DOCKER FILES AS WELL TO PRORPERLY PROPEGATE VALUES
not_found=None #"environemnt variable not found"
config_overlay = {
    "executor": {
        "name": environ.get("LATIGO_INSTANCE_NAME", "unnamed_executor"),
    },
    "task_queue": {
        "connection_string": environ.get("LATIGO_INTERNAL_EVENT_HUB", not_found),
    },
    "sensor_data": {
        "base_url": environ.get("LATIGO_TIME_SERIES_BASE_URL", not_found),
        "auth":{
            "resource": environ.get("LATIGO_TIME_SERIES_RESOURCE", not_found),
            "tenant" : environ.get("LATIGO_TIME_SERIES_TENANT", not_found),
            "authority_host_url" : environ.get("LATIGO_TIME_SERIES_AUTH_HOST_URL", not_found),
            "client_id" : environ.get("LATIGO_TIME_SERIES_CLIENT_ID", not_found),
            "client_secret" : environ.get("LATIGO_TIME_SERIES_CLIENT_SECRET", not_found),
        },
    },
    "prediction_storage": {
        "base_url": environ.get("LATIGO_TIME_SERIES_BASE_URL", not_found),
        "auth":{
            "resource": environ.get("LATIGO_TIME_SERIES_RESOURCE", not_found),
            "tenant" : environ.get("LATIGO_TIME_SERIES_TENANT", not_found),
            "authority_host_url" : environ.get("LATIGO_TIME_SERIES_AUTH_HOST_URL", not_found),
            "client_id" : environ.get("LATIGO_TIME_SERIES_CLIENT_ID", not_found),
            "client_secret" : environ.get("LATIGO_TIME_SERIES_CLIENT_SECRET", not_found),
        },
    },
    "predictor": {
        "connection_string": environ.get("LATIGO_GORDO_CONNECTION_STRING", not_found),
        "auth":{
            "resource": environ.get("LATIGO_GORDO_RESOURCE", not_found),
            "tenant" : environ.get("LATIGO_GORDO_TENANT", not_found),
            "authority_host_url" : environ.get("LATIGO_GORDO_AUTH_HOST_URL", not_found),
            "client_id" : environ.get("LATIGO_GORDO_CLIENT_ID", not_found),
            "client_secret" : environ.get("LATIGO_GORDO_CLIENT_SECRET", not_found),
        },
    },
}
# fmt: on

config_filename = environ.get("LATIGO_EXECUTOR_CONFIG_FILE", "executor_config.yaml")

config = load_config(config_filename, config_overlay)
if not config:
    logger.error(f"Could not load configuration for executor from {config_filename}")
    sys.exit(1)

logger.info("Preparing Latigo Executor")
executor = PredictionExecutor(config)
logger.info("Running Latigo Executor")
executor.run()
logger.info("Stopping Latigo Executor")
