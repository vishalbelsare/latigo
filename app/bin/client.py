#!/usr/bin/env python
import logging
import time
import sys
from config import CONFIG, ENVIRONMENT

#CONFIG.exit_on_errors()

# Set up logging for this app
logging.basicConfig(
    level=CONFIG.DEBUG_LEVEL,
    format="%(asctime)s %(levelname)-4.4s %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ])

logger = logging.getLogger(__file__)
logging.getLogger("uamqp").setLevel(logging.WARNING)  # Way too verbose

logger.warning(f"Using config:{CONFIG}")

logger.info("Starting Gordo Client for IOC - Main")
# Pretend to do something
time.sleep(5.0)
logger.info("Stopping Gordo Client for IOC - Main")

