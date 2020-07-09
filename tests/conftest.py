# This setup is necessary as "tests/" folder is not inside "app/"
import json
import logging
import os
import sys
from unittest.mock import MagicMock, patch, Mock

import fakeredis
import inject
import pandas as pd
import pytest
from redis import StrictRedis
from requests import Response

latigo_path: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../app/"))
sys.path.insert(0, latigo_path)

from .mock_classes import MockSensorDataProvider
from latigo.executor import PredictionExecutor
from latigo.gordo import GordoModelInfoProvider
from latigo.scheduler import Scheduler
from latigo.time_series_api import TimeSeriesAPIClient


SCHEDULER_PREDICTION_DELAY = 1  # days
SCHEDULER_PREDICTION_INTERVAL = 5  # minutes


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
        "authority_host_url": "https://dummy-authority",
        "client_id": "dummy-client",
        "client_secret": "dummy-secret",
        "auto_adding_headers": {
            "Ocp-Apim-Subscription-Key": "key",
        }
    }


@pytest.fixture
def schedule_config(auth_config):
    return {
        "scheduler": {
            "continuous_prediction_start_time": "08:00",
            "continuous_prediction_interval": f"{SCHEDULER_PREDICTION_INTERVAL}m",
            "continuous_prediction_delay": f"{SCHEDULER_PREDICTION_DELAY}d",
            "run_at_once": False,
        },
        "model_info": {
            "type": "gordo",
            "connection_string": "https://api/gordo/v0/",
            "data_provider": {"debug": True, "n_retries": 5},
            "prediction_forwarder": {"debug": False, "n_retries": 5},
            "auth": auth_config,
        },
        "task_queue": {
            "type": "kafka",
            "connection_string": "Endpoint=sb://sb/;SharedAccessKeyName=name;SharedAccessKey=yd;EntityPath=path",
            "topic": "latigo_topic",
        },
        "models_metadata_info": {
            "type": "metadata_api",
            "base_url": "https://metadata",
            "auth": auth_config,
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
            "type": "time_series_api",
            "base_url": "https://api/timeseries/v0",
            "async": False,
            "auth": auth_config,
            "mock_data": [pd.Series(data=[1, 2, 3, 4, 5])],
        },
        "prediction_storage": {
            "type": "time_series_api",
            "base_url": "https://api/timeseries/v1.6",
            "async": False,
            "auth": auth_config,
        },
        "model_info": {
            "type": "gordo",
            "connection_string": "https://api/gordo/v0/",
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
        "prediction_metadata_storage": {
            "type": "metadata_api",
            "base_url": "https://metadata",
            "auth": auth_config,
        },
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
@patch("latigo.metadata_api.client.MetadataAPIClient._create_session", new=MagicMock())
@patch("latigo.time_series_api.client.get_auth_session", new=MagicMock())
def basic_executor(config, request) -> PredictionExecutor:
    # Create a new class to avoid shared state
    cls = type("TestPredictionExecutor", (PredictionExecutor,), {})
    if hasattr(request, "param") and request.param:
        # patch "_is_ready" to be able to stop the loop execution
        setattr(cls, '_is_ready', property(fget=is_executor_ready(), fset=lambda x, y: x))

    return cls(config=config)


def is_executor_ready():
    """Need to quit from the loop.

    First time return True to run the loop, second False to quit the loop.
    """
    executor_statuses = iter([True])

    def inner(self) -> bool:
        return next(executor_statuses, False)
    return inner


@pytest.fixture(autouse=True)
def configure_dependencies():
    inject.clear_and_configure(
        lambda binder: binder.bind(StrictRedis, fakeredis.FakeStrictRedis()), bind_in_runtime=False
    )
    yield
    inject.clear()


@pytest.fixture
@patch("latigo.time_series_api.client.get_auth_session", new=MagicMock())
def time_series_api_client(config) -> TimeSeriesAPIClient:
    return TimeSeriesAPIClient(config["sensor_data"])


@pytest.fixture
@patch("latigo.metadata_api.client.MetadataAPIClient._create_session", new=MagicMock())
@patch("latigo.task_queue.kafka.Producer", new=MagicMock())
@patch("latigo.scheduler.Scheduler._perform_auth_checks", new=MagicMock())
def scheduler(schedule_config, request) -> Scheduler:
    # Create a new class to avoid shared state
    cls = type("TestScheduler", (Scheduler,), {})
    if hasattr(request, "param") and request.param:
        # patch "_is_ready" to be able to stop the loop execution
        setattr(cls, '_is_ready', property(fget=is_scheduler_ready(request.param), fset=lambda x, y: x))

    scheduler = cls(schedule_config)
    scheduler.model_info_provider = Mock(spec=GordoModelInfoProvider)
    scheduler.model_info_provider.get_all_model_names_by_project.return_value = {"project": ["model"]}
    return scheduler


def is_scheduler_ready(statuses):
    """Need to quit from the loop.

    statuses: pass [True, True] for loop to be run twice.
        Default is one time run.
    """
    executor_statuses = iter(statuses or [True])

    def inner(self) -> bool:
        return next(executor_statuses, False)
    return inner


def make_response(
    content: dict = None, dumped_data: str = None, status_code: int = 200, reason: str = "OK"
) -> Response:
    response_obj = Response()
    response_obj.status_code = status_code
    response_obj._content = dumped_data if dumped_data else dump_any_dict(content).encode()
    response_obj.reason = reason
    return response_obj


def dump_any_dict(target: dict) -> str:
    return json.dumps(target, sort_keys=True, default=str)
