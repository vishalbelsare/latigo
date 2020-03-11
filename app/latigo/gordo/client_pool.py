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
import requests_ms_auth

from gordo.client.client import Client
from gordo.machine import Machine
from gordo.machine.dataset.data_provider.base import GordoBaseDataProvider
from gordo.machine.dataset.sensor_tag import SensorTag
from gordo.util.utils import capture_args
from requests_ms_auth import MsSessionConfig

logger = logging.getLogger(__name__)
# logging.getLogger().setLevel(logging.WARNING)


def gordo_config_hash(config: dict):
    key = "gordo"
    parts = [
        "scheme",
        "host",
        "port",
        "project",
        "target",
        "batch_size",
        "parallelism",
        "forward_resampled_sensors",
        "n_retries",
        "use_parquet",
    ]
    if config:
        for part in parts:
            key += part + str(config.get(part, ""))
    return key


def clean_gordo_client_args(raw: dict):
    whitelist = [
        "project",
        "target",
        "host",
        "port",
        "scheme",
        "metadata",
        "data_provider",
        "prediction_forwarder",
        "batch_size",
        "parallelism",
        "forward_resampled_sensors",
        "n_retries",
        "session",
        "use_parquet",
    ]
    args = {}
    for w in whitelist:
        args[w] = raw.get(w)
    return args


class GordoClientPool:
    def __init__(self, raw_config: dict):
        self.config = raw_config
        self.client_instances_by_hash: dict = {}
        self.client_instances_by_project: dict = {}
        self.client_auth_session: typing.Optional[requests.Session] = None
        self.allocate_instances()

    def __repr__(self):
        return f"GordoClientPool()"

    def allocate_instance(self, project: str):
        client = self.client_instances_by_project.get(project, None)
        if not client:
            # Patch to all disableing the use of OAuth2Session's when developing locally
            auth_config = self.config.get("auth", dict())
            session = self.get_auth_session(auth_config)
            config = {**self.config}
            config["project"] = project
            config["session"] = session
            key = gordo_config_hash(config)
            # logger.info(f" + Instanciating Gordo Client: {key}")
            client = self.client_instances_by_hash.get(key, None)
            if not client:
                clean_config = clean_gordo_client_args(config)
                try:
                    client = Client(**clean_config)
                    self.client_instances_by_hash[key] = client
                    self.client_instances_by_project[project] = client
                except requests.exceptions.HTTPError as http_error:
                    if 404 == http_error.response.status_code:
                        logger.warning(
                            f"Skipping client allocation for {project}, project not found"
                        )
                    else:
                        logger.error(
                            f"Skipping client allocation for {project} due to HTTP error ('{type(http_error)}'): '{http_error}'"
                        )
                except Exception as error:
                    logger.error(
                        f"Skipping client allocation for {project} due to unknown error ('{type(error)}'): '{error}' ",
                        exc_info=True,
                    )
                    logger.warning(
                        f"NOTE: Using gordo config:\n{pprint.pformat(clean_config)}"
                    )

        return client

    def allocate_instances(self):
        projects = self.config.get("projects", [])
        if not isinstance(projects, list):
            projects = [projects]
        for project in projects:
            self.allocate_instance(project)

    def get_auth_session(self, auth_config: dict):
        if not self.client_auth_session:
            # logger.info("CREATING SESSION:")
            self.client_auth_session = requests_ms_auth.MsRequestsSession(
                MsSessionConfig(**self.config.get('auth'))
            )
        return self.client_auth_session
