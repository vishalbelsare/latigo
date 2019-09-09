import logging
import time

logging.basicConfig(level=CONFIG.DEBUG_LEVEL)
logger = logging.getLogger(__name__)
logging.getLogger("uamqp").setLevel(logging.WARNING)  # Way too verbose


logger.info("Starting Gordo Client for IOC - Scheduler")
# Pretend to do something
time.sleep(5000)
logger.info("Stopping Gordo Client for IOC - Scheduler")
