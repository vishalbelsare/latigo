import typing
import random
import logging
import pprint
import numpy as np
import pandas as pd
import requests
from datetime import datetime
import latigo.utils
from latigo.prediction_execution import PredictionExecutionProviderInterface

from latigo.sensor_data import SensorData, PredictionData
from latigo.model_info import ModelInfoProviderInterface
from latigo.gordo.auth import create_auth_session
from latigo.gordo.client import Client

# from gordo_components.client import Client
from gordo_components.data_provider.base import GordoBaseDataProvider, capture_args
from gordo_components.client.forwarders import PredictionForwarder
from gordo_components.dataset.sensor_tag import SensorTag


logger = logging.getLogger(__name__)

gordo_client_instances_by_hash: dict = {}
gordo_client_instances_by_project: dict = {}
gordo_client_auth_session: typing.Optional[requests.Session] = None


class LatigoDataProvider(GordoBaseDataProvider):
    """
    A GordoBaseDataset that wraps Latigo spesific data providers
    """

    @capture_args
    def __init__(self, config):
        super().__init__()
        self.config = config
        if not self.config:
            raise Exception("No data_provider_config specified")
        data_provider_type = self.config.get("type", None)
        self.data_provider = None
        if "random" == data_provider_type:
            self.data_provider = RandomDataProvider(**config)
        elif "influx" == data_provider_type:
            self.data_provider = InfluxDataProvider(**config)
        elif "datalake" == data_provider_type:
            self.data_provider = DataLakeProvider(**config)

    def load_series(self, from_ts: datetime, to_ts: datetime, tag_list: typing.List[SensorTag], dry_run: typing.Optional[bool] = False) -> typing.Iterable[pd.Series]:
        if self.data_forwarder:
            yield from self.data_forwarder.load_series(from_ts, to_ts, tag_list, dry_run)

    def can_handle_tag(self, tag: SensorTag) -> bool:
        if self.data_forwarder:
            return self.data_forwarder.can_handle_tag(tag)
        return False


class LatigoPredictionForwarder(PredictionForwarder):
    """
    A Gordo PredictionForwarder that wraps Latigo spesific prediction forwarders
    """

    def __init__(self, config):
        super().__init__()
        self.config = config
        if not self.config:
            raise Exception("No prediction_forwarder_config specified")
        prediction_forwarder_type = self.config.get("type", None)
        self.prediction_forwarder = None
        if "random" == prediction_forwarder_type:
            self.prediction_forwarder = RandomDataProvider(**config)
        elif "influx" == prediction_forwarder_type:
            self.prediction_forwarder = InfluxDataProvider(**config)
        elif "datalake" == prediction_forwarder_type:
            self.prediction_forwarder = DataLakeProvider(**config)



def gordo_config_hash(config: dict):
    key = "gordo"
    parts = ["scheme", "host", "port", "project", "target", "gordo_version", "batch_size", "parallelism", "forward_resampled_sensors", "ignore_unhealthy_targets", "n_retries"]
    if config:
        for part in parts:
            key += part + config.get("scheme", "")
    return key


def clean_gordo_client_args(raw: dict):
    whitelist = ["project", "target", "host", "port", "scheme", "gordo_version", "metadata", "data_provider", "prediction_forwarder", "batch_size", "parallelism", "forward_resampled_sensors", "ignore_unhealthy_targets", "n_retries", "data_provider", "prediction_forwarder", "session"]
    args = {}
    for w in whitelist:
        args[w] = raw.get(w)
    logger.info(pprint.pformat(raw))
    logger.info(pprint.pformat(args))
    return args


def get_auth_session(auth_config: dict):
    global gordo_client_auth_session
    if not gordo_client_auth_session:
        logger.info("CREATING SESSION:")
        gordo_client_auth_session = create_auth_session(auth_config)
    return gordo_client_auth_session


def allocate_gordo_client_instances(raw_config: dict):
    projects = raw_config.get("projects", [])
    logger.warning("raw_config:")
    logger.warning(raw_config)
    auth_config = raw_config.get("auth", dict())
    session = get_auth_session(auth_config)
    if not isinstance(projects, list):
        projects = [projects]
    for project in projects:
        config = {**raw_config}
        config["project"] = project
        config["session"] = session
        key = gordo_config_hash(config)
        logger.info(f" + Instanciating Gordo Client: {key}")
        client = gordo_client_instances_by_hash.get(key, None)
        if not client:
            client = Client(**clean_gordo_client_args(config))
            gordo_client_instances_by_hash[key] = client
            gordo_client_instances_by_project[project] = client


def get_gordo_client_instance_by_project(project):
    return gordo_client_instances_by_project.get(project, None)


def _expand_gordo_connection_string(config: dict):
    if "connection_string" in config:
        connection_string = config.pop("connection_string")
        parts = latigo.utils.parse_gordo_connection_string(connection_string)
        if parts:
            config.update(parts)


class GordoPredictionExecutionProvider(PredictionExecutionProviderInterface):
    def __init__(self, config):
        self.config = config
        if not self.config:
            raise Exception("No predictor_config specified")
        _expand_gordo_connection_string(self.config)
        # Augment config with the latigo data provider and prediction forwarders
        self.data_provider_config = config.get("data_provider", {})
        self.config["data_provider"] = LatigoDataProvider(self.data_provider_config)
        self.prediction_forwarder_config = config.get("prediction_forwarder", {})
        self.config["prediction_forwarder"] = LatigoPredictionForwarder(self.prediction_forwarder_config)
        allocate_gordo_client_instances(config)

    def execute_prediction(self, prediction_name: str, data: SensorData) -> PredictionData:
        client = get_gordo_client_instance_by_project(prediction_name)
        if client:
            result = client.predict(data.time_range.from_time, data.time_range.to_time)
            pd = PredictionData(name=prediction_name, time_range=data.time_range, result=result)
            return pd


class GordoModelInfoProvider(ModelInfoProviderInterface):
    def _prepare_auth(self):
        self.auth_config = self.config.get("auth")
        if not self.auth_config:
            raise Exception("No auth_config specified")

    def __init__(self, config):
        self.config = config
        if not self.config:
            raise Exception("No predictor_config specified")
        self._prepare_auth()
        _expand_gordo_connection_string(self.config)
        allocate_gordo_client_instances(config)

    def get_model_info(self, model_name: str):
        """
        Return any information about a named prediction
        """
        return {}

    def get_models(self, filter: dict):
        """
        Return a list of predictions matching the given filter.
        """
        models = []
        projects = filter.get("project", [])
        if not isinstance(projects, list):
            projects = [projects]
            for project in projects:
                client = get_gordo_client_instance_by_project(project)
                if client:
                    meta_data = client.get_metadata()
                    logger.info(f"METADATA for {project}---------------------------------------------")
                    logger.info(pprint.pformat(meta_data))
                    models.append(meta_data)
        return models
