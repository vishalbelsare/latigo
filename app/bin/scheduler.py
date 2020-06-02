#!/usr/bin/env python
import logging

from bin.common import basic_config
from latigo.scheduler import Scheduler

logger = logging.getLogger("latigo")


if __name__ == "__main__":
    config = basic_config("scheduler")

    logger.info("Configuring Latigo Scheduler")
    scheduler = Scheduler(config)
    scheduler.print_summary()
    logger.info("Running Latigo Scheduler")
    scheduler.run()
    logger.info("Stopping Latigo Scheduler")
