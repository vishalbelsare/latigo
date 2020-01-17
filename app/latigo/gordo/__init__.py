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
from latigo.auth import create_auth_session

# from latigo.gordo.client import Client
from gordo_components.client.client import Client

from gordo_components.data_provider.base import GordoBaseDataProvider, capture_args
from gordo_components.client.utils import EndpointMetadata
from gordo_components.dataset.sensor_tag import SensorTag


logger = logging.getLogger(__name__)
# logging.getLogger().setLevel(logging.WARNING)


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
                        f"Skipping client allocation for {project} due to unknown error ('{type(error)}'): '{error}' "
                    )
                    logger.warning(f"NOTE: Using config {pprint.pformat(clean_config)}")
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
            self.client_auth_session = create_auth_session(auth_config)
        return self.client_auth_session


def _gordo_to_latigo_tag(gordo_tag: SensorTag) -> LatigoSensorTag:
    latigo_tag = LatigoSensorTag(gordo_tag.name, gordo_tag.asset)
    return latigo_tag


def _gordo_to_latigo_tag_list(
    gordo_tag_list: typing.List[SensorTag]
) -> typing.List[LatigoSensorTag]:
    latigo_tag_list: typing.List[LatigoSensorTag] = []
    for gordo_tag in gordo_tag_list:
        latigo_tag = _gordo_to_latigo_tag(gordo_tag)
        latigo_tag_list.append(latigo_tag)
    return latigo_tag_list


class PredictionForwarder:
    def __call__(
        self,
        *,
        predictions: pd.DataFrame = None,
        endpoint: EndpointMetadata = None,
        metadata: dict = dict(),
        resampled_sensor_data: pd.DataFrame = None,
    ) -> typing.Awaitable[None]:
        ...


class LatigoDataProvider(GordoBaseDataProvider):
    """
    A GordoBaseDataProvider that wraps Latigo spesific data providers
    """

    @capture_args
    def __init__(
        self,
        config: dict,
        sensor_data_provider: typing.Optional[SensorDataProviderInterface],
    ):
        super().__init__()
        self.latigo_config = config
        if self == config:
            raise Exception("Config was self")
        if type(config) == type(self):
            raise Exception(f"Config was same type as self {type(self)}")
        if not self.latigo_config:
            raise Exception("No data_provider_config specified")
        self.sensor_data_provider = sensor_data_provider
        # logger.warning("DEBUGGING:")         logger.warning(config)        logger.error("".join(traceback.format_stack()))

    def load_series(
        self,
        from_ts: datetime,
        to_ts: datetime,
        tag_list: typing.List[SensorTag],
        dry_run: typing.Optional[bool] = False,
    ) -> typing.Iterable[pd.Series]:
        if dry_run:
            raise NotImplementedError(
                "Dry run for LatigoDataProvider is not implemented"
            )
        if not tag_list:
            logger.warning(
                "LatigoDataProvider called with empty tag_list, returning none"
            )
            return
        if to_ts < from_ts:
            raise ValueError(
                f"LatigoDataProvider called with to_ts: {to_ts} before from_ts: {from_ts}"
            )
        if not self.sensor_data_provider:
            logger.warning("Skipping, no sensor_data_provider")
            return
        spec: SensorDataSpec = SensorDataSpec(
            tag_list=_gordo_to_latigo_tag_list(tag_list)
        )
        time_range = TimeRange(from_time=from_ts, to_time=to_ts)
        sensor_data, err = self.sensor_data_provider.get_data_for_range(
            spec, time_range
        )
        if err:
            logger.error(f"Could not load sensor data: {err}")
            return
        if not sensor_data:
            logger.error(f"No sensor data")
            return
        if not sensor_data.ok():
            logger.error(f"Sensor data not OK")
            return
        if not sensor_data.data:
            logger.error(f"No data.data")
            return
        data = sensor_data.data.to_gordo_dataframe(tags=tag_list, target_tags=[])
        if not data:
            logger.error(f"No gordo data")
            return
        # logger.info(data)
        for d in data:
            d = d[((d.index >= from_ts) & (d.index <= to_ts))]
            yield d
        return

    def can_handle_tag(self, tag: SensorTag) -> bool:
        if self.sensor_data_provider:
            if self.sensor_data_provider:
                return self.sensor_data_provider.supports_tag(tag=tag)
        return False

    def __repr__(self):
        return f"LatigoDataProvider(config={self.latigo_config}, sensor_data_provider={self.sensor_data_provider})"


class LatigoPredictionForwarder(PredictionForwarder):
    """
    A Gordo PredictionForwarder that wraps Latigo spesific prediction forwarders
    """

    def __init__(
        self,
        config: dict,
        prediction_storage_provider: typing.Optional[PredictionForwarder],
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

    def __repr__(self):
        return f"LatigoPredictionForwarder(config_type={type(self.latigo_config)}, prediction_storage_provider_type={type(self.prediction_storage_provider)}, config={self.latigo_config}, prediction_storage_provider={self.prediction_storage_provider})"


def gordo_config_hash(config: dict):
    key = "gordo"
    parts = [
        "scheme",
        "host",
        "port",
        "project",
        "target",
        "gordo_version",
        "batch_size",
        "parallelism",
        "forward_resampled_sensors",
        "ignore_unhealthy_targets",
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
        "gordo_version",
        "metadata",
        "data_provider",
        "prediction_forwarder",
        "batch_size",
        "parallelism",
        "forward_resampled_sensors",
        "ignore_unhealthy_targets",
        "n_retries",
        "session",
        "use_parquet",
    ]
    args = {}
    for w in whitelist:
        args[w] = raw.get(w)
    return args


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


def _get_model_meta(model_data: dict):
    meta = model_data.get("endpoint-metadata", {}).get("metadata", {})
    return meta


def _get_model_tag_list(model_data: dict) -> typing.List[LatigoSensorTag]:
    meta = _get_model_meta(model_data)
    tag_list_data = meta.get("dataset", {}).get("tag_list", {})
    tag_list = []
    for tag_data in tag_list_data:
        tag = LatigoSensorTag(name=tag_data.get("name"), asset=tag_data.get("asset"))
        tag_list.append(tag)
    # logger.info("MODEL 0 META TAG_LIST:" + pprint.pformat(tag_list))
    return tag_list


def _get_model_target_tag_list(model_data: dict):
    meta = _get_model_meta(model_data)
    target_tag_list = meta.get("dataset", {}).get("target_tag_list", {})
    # logger.info("MODEL 0 META TAG_LIST:"+pprint.pformat(tag_list))
    return target_tag_list


def _get_model_name(model_data: dict):
    model_name = model_data.get("name", "")
    # logger.info(f"MODEL NAME: {name}")
    return model_name


def _get_project_name(model_data: dict):
    project_name = model_data.get("project", "")
    # logger.info(f"MODEL NAME: {name}")
    return project_name


class GordoModelInfoProvider(ModelInfoProviderInterface):
    def _prepare_auth(self):
        self.auth_config = self.config.get("auth")
        if not self.auth_config:
            raise Exception("No auth_config specified")

    def __init__(self, config):
        self.config = config
        if not self.config:
            raise Exception("No model_info_config specified")
        self._prepare_auth()
        expand_gordo_connection_string(self.config)
        expand_gordo_data_provider(config=self.config, sensor_data_provider=None)
        expand_gordo_prediction_forwarder(
            config=self.config, prediction_storage_provider=None
        )
        self.gordo_pool = GordoClientPool(raw_config=self.config)

    def __str__(self):
        return f"GordoModelInfoProvider()"

    def get_models_data(
        self,
        projects: typing.Optional[typing.List] = None,
        model_names: typing.Optional[typing.List] = None,
    ) -> typing.List[typing.Dict]:
        models = []
        if not projects:
            projects = self.config.get("projects", [])
            if not isinstance(projects, list):
                projects = [projects]
        for project_name in projects:
            # logger.info(f"LOOKING AT PROJECT {project_name}")
            client = self.gordo_pool.allocate_instance(project_name)
            if client:
                meta_data = client.get_metadata()
                for model_name, model_data in meta_data.items():
                    if model_names and model_name not in model_names:
                        continue
                    model_data["model_name"] = model_name
                    model_data["project_name"] = project_name
                    models.append(model_data)
            else:
                logger.error(f"No client found for project '{project_name}', skipping")
        return models

    def get_all_models(self, projects: typing.List) -> typing.List[Model]:
        models_data = self.get_models_data(projects)
        models = []
        for model_data in models_data:
            if model_data:
                model = Model(
                    project_name=model_data.get("project_name", "unnamed"),
                    model_name=model_data.get("model_name", "unnamed"),
                    tag_list=_get_model_tag_list(model_data),
                    target_tag_list=_get_model_target_tag_list(model_data),
                )
                if model:
                    models.append(model)
        return models

    def get_model_by_key(
        self, project_name: str, model_name: str
    ) -> typing.Optional[Model]:
        models_data = self.get_models_data(
            projects=[project_name], model_names=[model_name]
        )
        if not models_data:
            return None
        model = None
        model_data = models_data[0]
        if model_data:
            model = Model(
                project_name=model_data.get("project_name", "unnamed"),
                model_name=model_data.get("model_name", "unnamed"),
                tag_list=_get_model_tag_list(model_data),
                target_tag_list=_get_model_target_tag_list(model_data),
            )
        return model

    def get_spec(
        self, project_name: str, model_name: str
    ) -> typing.Optional[SensorDataSpec]:
        model = self.get_model_by_key(project_name=project_name, model_name=model_name)
        if not model:
            return None
        spec = SensorDataSpec(tag_list=model.tag_list)
        return spec


def print_client_debug(client: typing.Optional[Client]):
    logger.info("Client:")
    if not client:
        logger.info("  None")
        return
    data = {
        "base_url": client.base_url,
        "watchman_endpoint": client.watchman_endpoint,
        "metadata": client.metadata,
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
        "ignore_unhealthy_targets": client.ignore_unhealthy_targets,
        # "endpoints": client.endpoints
    }
    logger.info(pprint.pformat(data))


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
        self, project_name: str, model_name: str, sensor_data: SensorDataSet
    ) -> PredictionDataSet:
        if not project_name:
            raise Exception("No project_name in gordo.execute_prediction()")
        if not model_name:
            raise Exception("No model_name in gordo.execute_prediction()")
        if not sensor_data:
            raise Exception("No sensor_data in gordo.execute_prediction()")
        if not sensor_data.data:
            logger.warning(
                f"No data in prediction for project '{project_name}' and model {model_name}"
            )
            return PredictionDataSet(
                time_range=sensor_data.time_range, data=None, meta_data={}
            )
        if len(sensor_data.data) < 1:
            logger.warning(
                f"Length of data < 1 in prediction for project '{project_name}' and model {model_name}"
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
            meta_data={project_name: project_name, model_name: model_name},
            time_range=sensor_data.time_range,
            data=result,
        )

        # raise NotImplementedError("HALP!")
        # return PredictionDataSet(time_range=sensor_data.time_range, data=None, meta_data={})
