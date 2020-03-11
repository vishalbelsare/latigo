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


class GordoModelInfoProvider(ModelInfoProviderInterface):
    def _prepare_auth(self):
        self.auth_config = self.config.get("auth")

    def __init__(self, config):
        self.config = config
        if not self.config:
            raise Exception("No machine_info_config specified")
        self._prepare_auth()
        expand_gordo_connection_string(self.config)
        expand_gordo_data_provider(config=self.config, sensor_data_provider=None)
        expand_gordo_prediction_forwarder(
            config=self.config, prediction_storage_provider=None
        )
        self.gordo_pool = GordoClientPool(raw_config=self.config)

    def __str__(self):
        return f"GordoModelInfoProvider()"

    def get_model_data(
        self,
        projects: typing.Optional[typing.List] = None,
        model_names: typing.Optional[typing.List] = None,
    ) -> typing.List[Machine]:
        machines: typing.List[Machine] = []
        if not projects:
            projects = self.config.get("projects", [])
            if not isinstance(projects, list):
                projects = [projects]
        for project_name in projects:
            # logger.info(f"LOOKING AT PROJECT {project_name}")
            client = self.gordo_pool.allocate_instance(project_name)
            if client:
                machines += client.get_machines()
            else:
                logger.error(f"No client found for project '{project_name}', skipping")
        return machines

    def get_all_models(self, projects: typing.List) -> typing.List[Model]:
        machines = self.get_model_data(projects)
        models = []
        for machine in machines:
            if machine:
                project_name = machine.project_name or "unnamed"
                model_name = machine.name or "unnamed"
                model = Model(
                    project_name=project_name,
                    model_name=model_name,
                    tag_list=machine.dataset.tag_list,
                    target_tag_list=machine.dataset.target_tag_list,
                )
                if model:
                    models.append(model)
        return models

    def get_machine_by_key(
        self, project_name: str, model_name: str
    ) -> typing.Optional[Model]:
        machines = self.get_model_data(
            projects=[project_name], model_names=[model_name]
        )
        if not machines:
            return None
        model = None
        machine = machines[0]
        if machine:
            project_name = machine.project_name or "unnamed"
            model_name = machine.name or "unnamed"
            model = Model(
                project_name=project_name,
                model_name=model_name,
                tag_list=machine.dataset.tag_list,
                target_tag_list=machine.dataset.target_tag_list,
            )
        return model

    def get_spec(
        self, project_name: str, model_name: str
    ) -> typing.Optional[SensorDataSpec]:
        model = self.get_machine_by_key(
            project_name=project_name, model_name=model_name
        )
        if not model:
            return None
        spec = SensorDataSpec(tag_list=model.tag_list)
        return spec
