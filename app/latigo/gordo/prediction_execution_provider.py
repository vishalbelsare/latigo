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

from .misc import *
from .client_pool import *

logger = logging.getLogger(__name__)


class GordoPredictionExecutionProvider(PredictionExecutionProviderInterface):
    def _prepare_projects(self):
        self.projects = self.config.get("projects", [])
        if not isinstance(self.projects, list):
            self.projects = [self.projects]

    def __init__(self, sensor_data_provider, prediction_storage_provider, config):
        self.config = config
        if not self.config:
            raise Exception("No predictor_config specified")
        expand_gordo_connection_string(self.config)
        expand_gordo_data_provider(
            self.config, sensor_data_provider=sensor_data_provider
        )
        expand_gordo_prediction_forwarder(
            self.config, prediction_storage_provider=prediction_storage_provider
        )
        self.gordo_pool = GordoClientPool(self.config)
        self._prepare_projects()

    def __str__(self):
        return f"GordoPredictionExecutionProvider({self.projects})"

    def execute_prediction(
        self, project_name: str, machine_name: str, sensor_data: SensorDataSet
    ) -> PredictionDataSet:
        if not project_name:
            raise Exception("No project_name in gordo.execute_prediction()")
        if not machine_name:
            raise Exception("No machine_name in gordo.execute_prediction()")
        if not sensor_data:
            raise Exception("No sensor_data in gordo.execute_prediction()")
        if not sensor_data.data:
            logger.warning(
                f"No data in prediction for project '{project_name}' and model {machine_name}"
            )
            return PredictionDataSet(
                time_range=sensor_data.time_range, data=None, meta_data={}
            )
        if len(sensor_data.data) < 1:
            logger.warning(
                f"Length of data < 1 in prediction for project '{project_name}' and model {machine_name}"
            )
            return PredictionDataSet(
                time_range=sensor_data.time_range, data=None, meta_data={}
            )
        client = self.gordo_pool.allocate_instance(project_name)
        if not client:
            raise Exception(
                f"No gordo client found for project '{project_name}' in gordo.execute_prediction()"
            )
        print_client_debug(client)
        result = client.predict(
            start=sensor_data.time_range.from_time, end=sensor_data.time_range.to_time
        )
        # logger.info(f"PREDICTION RESULT: {result}")
        if not result:
            raise Exception("No result in gordo.execute_prediction()")
        return PredictionDataSet(
            meta_data={project_name: project_name, machine_name: machine_name},
            time_range=sensor_data.time_range,
            data=result,
        )
