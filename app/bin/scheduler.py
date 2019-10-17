#!/usr/bin/env python

import sys
from os import environ

from latigo.log import setup_logging

logger = setup_logging("latigo.app.scheduler")
from latigo.utils import load_yaml, merge
from latigo.scheduler import Scheduler


logger.info("Starting Latigo - Scheduler")

config_filename = environ.get("LATIGO_SCHEDULER_CONFIG_FILE", "scheduler_config.yaml")

config_base, failure = load_yaml(config_filename)
if not config_base:
    logger.error(f"Could not load configuration for scheduler from {config_filename}: {failure}")
    sys.exit(1)

# Augment loaded config with secrets from environment
# fmt: off
config_secrets = {
    "scheduler": {
        "name": environ.get("LATIGO_INSTANCE_NAME", "unnamed_scheduler")
    },
    "task_queue": {
        "connection_string": environ.get("LATIGO_INTERNAL_EVENT_HUB", "NOT SET")
    },
    "db": {
        "connection_string": environ.get("LATIGO_INTERNAL_DATABASE", "NOT SET")
    }
}
# fmt: on

config = {}
merge(config_base, config)
merge(config_secrets, config)
logger.info("Preparing Latigo - Scheduler")

scheduler = Scheduler(config)
logger.info("Running Latigo - Scheduler")
scheduler.run()
logger.info("Stopping Latigo - Scheduler")
