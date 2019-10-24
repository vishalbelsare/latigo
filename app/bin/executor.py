#!/usr/bin/env python

import sys
import pprint
from os import environ
from latigo.log import setup_logging

logger = setup_logging("latigo.app.executor")
from latigo.utils import load_yaml, merge
from latigo.executor import PredictionExecutor

config_filename = environ.get("LATIGO_EXECUTOR_CONFIG_FILE", "executor_config.yaml")
logger.info(f"Starting Latigo - Executor with configuration from {config_filename}")

config_base, failure = load_yaml(config_filename)
if not config_base:
    logger.error(f"Could not load configuration for executor from {config_filename}: {failure}")
    sys.exit(1)

# Augment loaded config with secrets from environment
# fmt: off
# NOTE: REMEMBER TO UPDATE DOCKER FILES AS WELL TO PRORPERLY PROPEGATE VALUES
config_secrets = {
    "executor": {
        "name": environ.get("LATIGO_INSTANCE_NAME", "unnamed_executor"),
    },
    "task_queue": {
        "connection_string": environ.get("LATIGO_INTERNAL_EVENT_HUB", "NOT SET"),
    },
    "db": {
        "connection-string": environ.get("LATIGO_INTERNAL_DATABASE", "NOT SET"),
    },
    "sensor-data": {
        "connection-string": environ.get("LATIGO_SENSOR_DATA_CONNECITON", "NOT SET"),
    },
    "prediction-storage": {
        "connection-string": environ.get("LATIGO_PREDICTION_STORAGE_CONNECITON", "NOT SET"),
    },
    "predictor": {
        "auth":{
            "resource": environ.get("LATIGO_GORDO_RESOURCE", "NOT SET"),
            "tenant" : environ.get("LATIGO_GORDO_TENANT", "NOT SET"),
            "authority_host_url" : environ.get("LATIGO_GORDO_AUTH_HOST_URL", "NOT SET"),
            "client_id" : environ.get("LATIGO_GORDO_CLIENT_ID", "NOT SET"),
            "client_secret" : environ.get("LATIGO_GORDO_CLIENT_SECRET", "NOT SET"),
        },
    },
}
# fmt: on


config = {}
merge(config_base, config)
merge(config_secrets, config)
logger.info("Preparing Latigo - Executor")

executor = PredictionExecutor(config)
logger.info("Running Latigo - Executor")
executor.run()
logger.info("Stopping Latigo - Executor")
