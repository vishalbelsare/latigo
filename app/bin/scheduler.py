#!/usr/bin/env python

import distutils.util
import os
import socket
import sys
import threading
from latigo.log import setup_logging
from latigo import __version__ as latigo_version

logger = setup_logging("latigo.app.scheduler")
from latigo.utils import load_configs, sleep
from latigo.scheduler import Scheduler


config, err = load_configs(
    "../deploy/scheduler_config.yaml",
    os.environ["LATIGO_SCHEDULER_CONFIG_FILE"] or None,
)
if not config:
    logger.error(f"Could not load configuration for scheduler: {err}")
    sleep(60 * 5)
    sys.exit(1)

threading.current_thread().name = config.get("scheduler", {}).get(
    "instance_name", f"latigo-scheduler-{latigo_version}-{socket.getfqdn()}"
)

logger.info("Configuring Latigo Scheduler")
scheduler = Scheduler(config)
scheduler.print_summary()
logger.info("Running Latigo Scheduler")
scheduler.run()
logger.info("Stopping Latigo Scheduler")
