#!/usr/bin/env python

import time
from config import CONFIG, ENVIRONMENT
import log
import logging
import sys

#CONFIG.exit_on_errors()

# Set up logging for this app
log.setup_logging()

logger = logging.getLogger(__file__)

logger.warning(f"Using config:{CONFIG}")

logger.info("Starting Latigo - Scheduler")
# Pretend to do something
while True:
    logger.info(" + Latigo - Scheduler")
    time.sleep(5.0)

logger.info("Stopping Latigo - Scheduler")

