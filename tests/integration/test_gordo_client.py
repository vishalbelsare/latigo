import json
import pandas as pd
import typing
from datetime import datetime, timedelta
import logging
import pprint
from os import environ
from latigo.gordo import GordoModelInfoProvider, GordoPredictionExecutionProvider, LatigoDataProvider, LatigoPredictionForwarder, clean_gordo_client_args, expand_gordo_connection_string, expand_gordo_data_provider, expand_gordo_prediction_forwarder
from latigo.sensor_data import MockSensorDataProvider, sensor_data_provider_factory
from latigo.prediction_storage import MockPredictionStorageProvider, prediction_storage_provider_factory
from latigo.types import TimeRange, SensorDataSet
from latigo.utils import rfc3339_from_datetime, datetime_from_rfc3339

logger = logging.getLogger(__name__)

# Turn down noiselevel from gordo
logging.getLogger("gordo_components").setLevel(logging.WARNING)

dummy_provider = MockSensorDataProvider({"mock_data": [pd.Series(data=[1, 2, 3, 4, 5])]})
dummy_prediction_forwarder = MockPredictionStorageProvider({"mock_data": [pd.Series(data=[1, 2, 3, 4, 5])]})


def _get_config():
    not_found = "Not found in environment variables"
    # fmt: off
    return {
        "projects": ['ioc-1130'],
        "connection_string": environ.get("LATIGO_GORDO_CONNECTION_STRING", not_found),
        "batch_size": 1000,
        "parallelism": 10,
        "forward_resampled_sensors": False,
        "ignore_unhealthy_targets": True,
        "n_retries": 5,
        "data_provider":{
            "debug": True,
            "n_retries": 5,
            },
        "prediction_forwarder":{
            "debug": False,
            "n_retries": 5,
            },
        "auth": {
            "resource": environ.get("LATIGO_GORDO_RESOURCE", not_found),
            "tenant": environ.get("LATIGO_GORDO_TENANT", not_found),
            "authority_host_url": environ.get("LATIGO_GORDO_AUTH_HOST_URL", not_found),
            "client_id": environ.get("LATIGO_GORDO_CLIENT_ID", not_found),
            "client_secret": environ.get("LATIGO_GORDO_CLIENT_SECRET", not_found)
        }
    }
    # fmt: on


def test_gordo_config_expansion():
    config = _get_config()
    # Augment config with expanded gordo connection string
    expand_gordo_connection_string(config)
    # Augment config with the latigo data provider
    expand_gordo_data_provider(config, dummy_provider)
    # Augment config with the latigo prediction forwarder
    expand_gordo_prediction_forwarder(config, dummy_prediction_forwarder)


def un_test_gordo_client_pool():
    config = _get_config()
    # GordoClientPool
    pass


def test_model_info():
    config = _get_config()
    # logger.info("CONFIG:")
    # logger.info(pprint.pformat(config))
    gordo_model_info_provider = GordoModelInfoProvider(config)
    model_info = gordo_model_info_provider.get_model_info()
    # logger.info("MODELS:"+pprint.pformat(models))
    assert model_info is not None
    models = model_info.get_all()
    num = 10
    for i in range(num):
        model = models[i]
        # with open('/tmp/model.json', 'w') as fp:
        #    json.dump(model, fp, indent=4, sort_keys=True)
        spec = model.get_spec()
        logger.info(f"PROJECT:{model.project_name} MODEL:{model.model_name}({i}) TAG_LIST: {pprint.pformat(model.tag_list)} TARGET_TAG_LIST: {pprint.pformat(model.target_tag_list)} SPEC:{spec}")


def un_test_prediction_execution():
    config = _get_config()
    logger.info("CONFIG:")
    logger.info(pprint.pformat(config))
    gordo_prediction_execution_provider = GordoPredictionExecutionProvider(dummy_provider, dummy_prediction_forwarder, config)
    project_name: str = config.get("projects", ["no-projects-in-config"])[0]
    model_name: str = "lol"
    logger.info("Prediction for project_name={project_name} and model_name={model_name}")
    from_time = datetime_from_rfc3339("2019-01-02T00:00:00Z")
    to_time = datetime_from_rfc3339("2019-02-02T00:00:00Z")
    time_range = TimeRange(from_time=from_time, to_time=to_time)
    data = None
    sensor_data: SensorData = SensorData(time_range=time_range, data=data)
    prediction_data = gordo_prediction_execution_provider.execute_prediction(project_name=project_name, model_name=model_name, sensor_data=sensor_data)
    assert prediction_data != None
