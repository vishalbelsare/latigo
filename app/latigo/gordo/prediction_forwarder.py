import typing
import logging
import pprint
import pandas as pd
import requests
import copy
import abc
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
from latigo.prediction_storage import PredictionStorageProviderInterface

from gordo.client.client import Client
from gordo.machine import Machine
from gordo.machine.dataset.data_provider.base import GordoBaseDataProvider
from gordo.machine.dataset.sensor_tag import SensorTag
from gordo.util.utils import capture_args

# from gordo.client.forwarders import PredictionForwarder


logger = logging.getLogger(__name__)


class PredictionForwarder(metaclass=abc.ABCMeta):

    """
    Definition of a callable which the :class:`gordo.client.Client`
    will call after each successful prediction response::
        def my_forwarder(
            predictions: pd.DataFrame = None,
            machine: Machine = None,
            metadata: dict = dict(),
            resampled_sensor_data: pd.DataFrame = None
        ):
            ...
    """

    @abc.abstractmethod
    def __call__(
        self,
        *,
        predictions: pd.DataFrame = None,
        machine: Machine = None,
        metadata: dict = dict(),
        resampled_sensor_data: pd.DataFrame = None,
    ):
        ...


class LatigoPredictionForwarder(PredictionForwarder):
    """
    A Gordo PredictionForwarder that wraps Latigo spesific prediction forwarders
    """

    def __init__(
        self,
        config: dict,
        prediction_storage_provider: typing.Optional[
            PredictionStorageProviderInterface
        ],
    ):
        super().__init__()
        self.latigo_config = config
        if self == config:
            raise Exception("Config was self")
        if type(config) == type(self):
            raise Exception(f"Config was same type as self {type(self)}")
        if not self.latigo_config:
            raise Exception("No prediction_forwarder_config specified")
        self.prediction_storage_provider = prediction_storage_provider

    def __call__(
        self,
        *,
        predictions: pd.DataFrame = None,
        machine: Machine = None,
        metadata: dict = dict(),
        resampled_sensor_data: pd.DataFrame = None,
    ):
        # if self.prediction_storage_provider:
        # self.prediction_storage_provider.put_prediction(predictions)
        pass

    def __repr__(self):
        return f"LatigoPredictionForwarder(config_type={type(self.latigo_config)}, prediction_storage_provider_type={type(self.prediction_storage_provider)}, config={self.latigo_config}, prediction_storage_provider={self.prediction_storage_provider})"
