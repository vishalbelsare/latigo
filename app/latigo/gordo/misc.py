import typing
import logging
import pprint
import pandas as pd
import requests
import copy
from datetime import datetime
import latigo.utils
from latigo.prediction_execution import PredictionExecutionProviderInterface

from latigo.types import (
    TimeRange,
    SensorDataSpec,
    SensorDataSet,
    PredictionDataSet,
    LatigoSensorTag,
)
from latigo.sensor_data import SensorDataProviderInterface

from latigo.model_info import ModelInfoProviderInterface, Model

from gordo.client.client import Client
from gordo.machine import Machine
from gordo.machine.dataset.data_provider.base import GordoBaseDataProvider
from gordo.machine.dataset.sensor_tag import SensorTag
from gordo.util.utils import capture_args

from .data_provider import *
from .prediction_forwarder import *


logger = logging.getLogger(__name__)


def expand_gordo_connection_string(config: dict):
    if "connection_string" in config:
        connection_string = config.pop("connection_string")
        parts = latigo.utils.parse_gordo_connection_string(connection_string)
        if parts:
            config.update(parts)
        else:
            raise Exception(
                f"Could not parse gordo connection string: {connection_string}"
            )


def expand_gordo_data_provider(
    config: dict, sensor_data_provider: typing.Optional[SensorDataProviderInterface]
):
    data_provider_config = config.get("data_provider", {})
    config["data_provider"] = LatigoDataProvider(
        config=copy.deepcopy(data_provider_config),
        sensor_data_provider=sensor_data_provider,
    )


def expand_gordo_prediction_forwarder(config: dict, prediction_storage_provider):
    prediction_forwarder_config = config.get("prediction_forwarder", {})
    config["prediction_forwarder"] = LatigoPredictionForwarder(
        config=copy.deepcopy(prediction_forwarder_config),
        prediction_storage_provider=prediction_storage_provider,
    )


def print_client_debug(client: typing.Optional[Client]):
    logger.info("Client:")
    if not client:
        logger.info("  None")
        return
    data = {
        "base_url": client.base_url,
        "metadata": client.metadata,
        "revision": client.revision,
        "prediction_forwarder": client.prediction_forwarder,
        "data_provider": client.data_provider,
        "use_parquet": client.use_parquet,
        "session": client.session,
        "prediction_path": client.prediction_path,
        "batch_size": client.batch_size,
        "parallelism": client.parallelism,
        "forward_resampled_sensors": client.forward_resampled_sensors,
        "n_retries": client.n_retries,
        "query": client.query,
        "target": client.target,
    }
    logger.info(pprint.pformat(data))
