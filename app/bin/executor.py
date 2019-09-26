#!/usr/bin/env python
from latigo.log import *

import time
import logging
import sys
import os
from latigo.executor import *

logger=setup_logging(__file__)

logger.info("Starting Latigo - Executor")
executor = PredictionExecutor()
logger.info("Running Latigo - Executor")
executor.run()
logger.info("Stopping Latigo - Executor")
