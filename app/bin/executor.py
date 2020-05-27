#!/usr/bin/env python
import copy

from common import basic_config
from latigo.executor import PredictionExecutor

if __name__ == "__main__":
    config = basic_config("executor")

    executor = PredictionExecutor(config=copy.deepcopy(config))
    executor.print_summary()
    executor.run()
