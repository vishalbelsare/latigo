#!/usr/bin/env python

import distutils.util
import os
import socket
import sys
import threading
from latigo.log import setup_logging

logger = setup_logging("latigo.app.scheduler")
from latigo.utils import load_config
from latigo.scheduler import Scheduler


# Augment loaded config with variables from environment
# fmt: off
# NOTE: REMEMBER TO UPDATE DOCKER FILES AS WELL TO PRORPERLY PROPEGATE VALUES
not_found=None # "environemnt variable not found"

verify_auth = bool(distutils.util.strtobool(os.environ.get("LATIGO_ENABLE_AUTH_VERIFICATION", "True")))
if not verify_auth:
    logger.warning("Authentication verification disbled! Enable for production.")

config_overlay = {
    "scheduler": {
        "projects": os.environ.get("LATIGO_SCHEDULER_PROJECTS", "lat-lit"),
        "continuous_prediction_start_time": os.environ.get("LATIGO_SCHEDULER_PREDICTION_START_TIME", "08:00"),
        "continuous_prediction_interval": os.environ.get("LATIGO_SCHEDULER_PREDICTION_INTERVAL", "90m"),
        "continuous_prediction_delay": os.environ.get("LATIGO_SCHEDULER_PREDICTION_DELAY", "1d"),
        "name": os.environ.get("LATIGO_INSTANCE_NAME", "unnamed_scheduler"),
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
        "enable_auth": verify_auth,
    },
    "enable_auth_verification": verify_auth,
}
# fmt: on

config_filename = os.environ.get(
    "LATIGO_SCHEDULER_CONFIG_FILE", "scheduler_config.yaml"
)

config = load_config(config_filename, config_overlay)
if not config:
    logger.error(f"Could not load configuration for scheduler from {config_filename}")
    sys.exit(1)

threading.current_thread().name = config.get("scheduler", {}).get(
    "instance_name", "latigo-scheduler-" + socket.getfqdn()
)

logger.info("Configuring Latigo Scheduler")
scheduler = Scheduler(config)
logger.info("Running Latigo Scheduler")
scheduler.run()
logger.info("Stopping Latigo Scheduler")
