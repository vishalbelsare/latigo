#!/usr/bin/env python

import time
from config import CONFIG, ENVIRONMENT
import log
import logging
import sys
import os

#CONFIG.exit_on_errors()
print("BOB's your auntie")
sys.exit(200)
# Set up logging for this app
log.setup_logging()

logger = logging.getLogger(__file__)

logger.warning(f"Using config:{CONFIG}")

logger.info("Starting Latigo - Executor")


event_hub_connection_string = os.environ.get('LATIGO_EXECUTOR_EVENT_HUB', "fdkjgkfdjgkfdgjkfdg")
storage=MockPredictionStorageProvider()

executor=PredictionExecutor(event_hub_connection_string, storage)

executor.run()

logger.info("Stopping Latigo - Executor")

