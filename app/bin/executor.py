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


{"db": {"connection-string": "postgresql://postgres:example@postgres:5432/postgres"}, latigo - executor - 2 | "executor": {"name": '"latigo-executor-2"'}, latigo - executor - 2 | "prediction-storage": {"connection-string": "Endpoint=sb://lroll-gordo-client-ioc.servicebus.windows.net/;SharedAccessKeyName=lroll-gordo-ioc-ap;SharedAccessKey=qdwVEVM0dDfFprrP0wHHPWGurgLEGlKiG9rOJiC/UTY=;EntityPath=gordo-in"}, latigo - executor - 2 | "sensor-data": {"connection-string": "Endpoint=sb://lroll-gordo-client-ioc.servicebus.windows.net/;SharedAccessKeyName=lroll-gordo-ioc-ap;SharedAccessKey=qdwVEVM0dDfFprrP0wHHPWGurgLEGlKiG9rOJiC/UTY=;EntityPath=gordo-in"}, latigo - executor - 2 | "task_queue": {"connection_string": "Endpoint=sb://lroll-gordo-client-ioc.servicebus.windows.net/;SharedAccessKeyName=lroll-gordo-ioc-ap;SharedAccessKey=qdwVEVM0dDfFprrP0wHHPWGurgLEGlKiG9rOJiC/UTY=;EntityPath=gordo-in"}}
latigo - executor - 2 | (
    {
        "db": {"connection_string": "DO NOT PUT SECRETS IN THIS FILE"},
        latigo - executor - 2 | "prediction_data": {"connection_string": "DO NOT PUT SECRETS IN THIS FILE", latigo - executor - 2 | "debug": False, latigo - executor - 2 | "n_retries": 5, latigo - executor - 2 | "partition": "0", latigo - executor - 2 | "type": "timeseries-api"},
        latigo - executor - 2 | "predictor": {"batch_size": 1000, latigo - executor - 2 | "data_provider": None, latigo - executor - 2 | "forward_resampled_sensors": False, latigo - executor - 2 | "gordo_version": "v0", latigo - executor - 2 | "host": "localhost", latigo - executor - 2 | "ignore_unhealthy_targets": True, latigo - executor - 2 | "metadata": None, latigo - executor - 2 | "n_retries": 5, latigo - executor - 2 | "parallelism": 10, latigo - executor - 2 | "port": 8888, latigo - executor - 2 | "prediction_forwarder": None, latigo - executor - 2 | "project": "1130-gordo-tilstandomatic", latigo - executor - 2 | "scheme": "http", latigo - executor - 2 | "target": None, latigo - executor - 2 | "type": "gordo"},
        latigo - executor - 2 | "sensor_data": {"connection_string": "DO NOT PUT SECRETS IN THIS FILE", latigo - executor - 2 | "debug": False, latigo - executor - 2 | "n_retries": 5, latigo - executor - 2 | "partition": "0", latigo - executor - 2 | "type": "timeseries-api"},
        latigo - executor - 2 | "task_queue": {"connection_string": "DO NOT PUT SECRETS IN THIS FILE", latigo - executor - 2 | "do_trace": True, latigo - executor - 2 | "name": "executor_task_queue"},
    },
    latigo - executor - 2 | None,
)
