#!/usr/bin/env python

import sys
from os import environ
import pprint
from latigo.log import setup_logging

logger = setup_logging("latigo.app.scheduler")
from latigo.utils import load_config
from latigo.scheduler import Scheduler


logger.info("Starting Latigo Scheduler")

# Augment loaded config with variables from environment
# fmt: off
# NOTE: REMEMBER TO UPDATE DOCKER FILES AS WELL TO PRORPERLY PROPEGATE VALUES
not_found=None #"environemnt variable not found"

config_overlay = {
    "scheduler": {
        "projects": environ.get("LATIGO_SCHEDULER_PROJECTS", "ioc-1130, ioc-1125"),
        "continuous_prediction_start_time": environ.get("LATIGO_SCHEDULER_PREDICTION_START_TIME", "08:00"),
        "continuous_prediction_interval": environ.get("LATIGO_SCHEDULER_PREDICTION_INTERVAL", "90m"),
        "continuous_prediction_delay": environ.get("LATIGO_SCHEDULER_PREDICTION_DELAY", "1d"),
        "name": environ.get("LATIGO_INSTANCE_NAME", "unnamed_scheduler"),
    },
    "task_queue": {
        "connection_string": environ.get("LATIGO_INTERNAL_EVENT_HUB", not_found),
    },
    "model_info":{
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

config_filename = environ.get("LATIGO_SCHEDULER_CONFIG_FILE", "scheduler_config.yaml")

config = load_config(config_filename, config_overlay)
if not config:
    logger.error(f"Could not load configuration for scheduler from {config_filename}")
    sys.exit(1)

logger.info("Preparing Latigo Scheduler")
scheduler = Scheduler(config)
logger.info("Running Latigo Scheduler")
scheduler.run()
logger.info("Stopping Latigo Scheduler")
