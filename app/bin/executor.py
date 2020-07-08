#!/usr/bin/env python
import copy
import os

import inject
from redis import StrictRedis

from bin.common import basic_config
from latigo.executor import PredictionExecutor


def inject_config(binder):
    """Application components boilerplate."""
    binder.bind(StrictRedis, StrictRedis(
        host=os.environ["CACHE_HOST"],
        password=os.environ["CACHE_PASSWORD"],
        port=os.environ["CACHE_PORT"],
        ssl=True,
    ))


if __name__ == "__main__":
    # Configure all dependencies only when the service is ready
    inject.configure_once(inject_config, bind_in_runtime=False)

    config = basic_config("executor")

    executor = PredictionExecutor(config=copy.deepcopy(config))
    executor.print_summary()
    executor.run()
