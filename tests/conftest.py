# This setup is necessary as "tests/" folder is not inside "app/"
import logging
import os
import sys
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

latigo_path: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../app/"))
sys.path.insert(0, latigo_path)

from .mock_classes import MockSensorDataProvider
from latigo.executor import PredictionExecutor
from latigo.gordo import GordoModelInfoProvider


SCHEDULER_PREDICTION_DELAY = 1  # days
SCHEDULER_PREDICTION_INTERVAL = 90  # minutes


def setup_single_log_level(level: int = logging.INFO):
    """Set new level of logging for root logger.

    Needed to disable lots DEBUG messages from multiple loggers.
    """
    logging.getLogger().setLevel(level)


setup_single_log_level()


@pytest.fixture
def auth_config():
    return {
        "resource": "dummy-resource",
        "tenant": "dummy-tenant",
        "authority_host_url": "dummy-authority",
        "client_id": "dummy-client",
        "client_secret": "dummy-secret",
    }


@pytest.fixture
def schedule_config(auth_config):
    return {
        "scheduler": {
            "continuous_prediction_start_time": "08:00",
            "continuous_prediction_interval": f"{SCHEDULER_PREDICTION_INTERVAL}m",
            "continuous_prediction_delay": f"{SCHEDULER_PREDICTION_DELAY}d",
            "projects": ["pr-2020"],
            "back_fill_max_interval": "7d",
            "restart_interval_sec": 0,
            "run_at_once": True,
        },
        "model_info": {
            "auth": auth_config,
        },
        "task_queue": {
            "type": "kafka",
            "connection_string": "Endpoint=sb://sb/;SharedAccessKeyName=name;SharedAccessKey=yd;EntityPath=path",
            "topic": "latigo_topic",
        }
    }


@pytest.fixture
def config(auth_config):
    return {
        "executor": {"instance_count": 1, "log_debug_enabled": False},
        "task_queue": {
            "type": "mock",
            "connection_string": "dummy",
            "security.protocol": "SASL_SSL",
            "ssl.ca.location": "/etc/ssl/certs/ca-certificates.crt",
            "sasl.mechanism": "PLAIN",
            "group.id": "1",
            "client.id": "executor",
            "request.timeout.ms": 10000,
            "session.timeout.ms": 10000,
            "default.topic.config": {"auto.offset.reset": "earliest"},
            "debug": "fetch",
            "topic": "latigo_topic",
            "enable.auto.commit": True,
            "auto.commit.interval.ms": 1000,
        },
        "sensor_data": {
            "type": "mock",
            "base_url": "dummy",
            "async": False,
            "auth": auth_config,
            "mock_data": [pd.Series(data=[1, 2, 3, 4, 5])],
        },
        "prediction_storage": {
            "type": "mock",
            "base_url": "dummy",
            "async": False,
            "auth": auth_config,
            "mock_data": [pd.Series(data=[1, 2, 3, 4, 5])],
        },
        "model_info": {
            "type": "gordo",
            "connection_string": "dummy",
            "projects": ["project-1", "project-2"],
            "target": None,
            "metadata": None,
            "batch_size": 1000,
            "parallelism": 10,
            "forward_resampled_sensors": False,
            "ignore_unhealthy_targets": True,
            "n_retries": 5,
            "data_provider": {"debug": True, "n_retries": 5},
            "prediction_forwarder": {"debug": False, "n_retries": 5},
            "auth": auth_config,
        },
        "predictor": {
            "type": "gordo",
            "connection_string": "https://base_url/gordo/v1/",
            "target": None,
            "metadata": None,
            "batch_size": 1000,
            "parallelism": 10,
            "forward_resampled_sensors": False,
            "ignore_unhealthy_targets": True,
            "n_retries": 5,
            "data_provider": {"debug": True, "n_retries": 5},
            "prediction_forwarder": {"debug": False, "n_retries": 5},
            "auth": auth_config,
        },
        "prediction_metadata_storage": {"type": "mock", "auth": auth_config},
    }


@pytest.fixture
def sensor_data_provider(config):
    return MockSensorDataProvider(config.get("sensor_data"))


@pytest.fixture
def prediction_forwarder(MockPredictionStorageProvider):
    return MockPredictionStorageProvider(config.get("prediction_storage"))


@pytest.fixture
@patch(
    "latigo.executor.model_info_provider_factory", new=MagicMock(side_effect=MagicMock(spec_set=GordoModelInfoProvider))
)
@patch("latigo.gordo.prediction_execution_provider.GordoClientPool", new=MagicMock())
@patch("latigo.executor.PredictionExecutor._perform_auth_checks", new=MagicMock())
def basic_executor(config, request) -> PredictionExecutor:
    if hasattr(request, "param") and request.param:
        # patch "_is_ready" to be able to stop the loop execution
        setattr(PredictionExecutor, '_is_ready', property(fget=is_executor_ready(), fset=lambda x, y: x))

    return PredictionExecutor(config=config)


def is_executor_ready():
    """Need to quit from the loop.

    First time return True to run the loop, second False to quit the loop.
    """
    executor_statuses = [False, True]  # pop() will be used -> order starts from the end of the List

    def inner(self) -> bool:
        return executor_statuses.pop()
    return inner
