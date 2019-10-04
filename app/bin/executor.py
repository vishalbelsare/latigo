#!/usr/bin/env python

from latigo.log import setup_logging
from latigo.executor import PredictionExecutor

logger = setup_logging('latigo.app.executor')

logger.info("Starting Latigo - Executor")
executor = PredictionExecutor()
logger.info("Running Latigo - Executor")
executor.run()
logger.info("Stopping Latigo - Executor")
