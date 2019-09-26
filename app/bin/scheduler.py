#!/usr/bin/env python
from latigo.log import *

import time
import logging
import sys
from latigo.scheduler import *

logger=setup_logging(__file__)

logger.info("Starting Latigo - Scheduler")
scheduler = Scheduler()
scheduler.run()
logger.info("Stopping Latigo - Scheduler")

