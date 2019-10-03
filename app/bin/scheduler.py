#!/usr/bin/env python
from latigo.log import setup_logging

from latigo.scheduler import Scheduler

logger = setup_logging(__file__)

logger.info("Starting Latigo - Scheduler")
scheduler = Scheduler()
scheduler.run()
logger.info("Stopping Latigo - Scheduler")
