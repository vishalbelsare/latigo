import logging
import pprint
from os import environ
from latigo.executor import PredictionExecutor

logger = logging.getLogger(__name__)

# dummy_provider = MockSensorDataProvider({"mock_data": [pd.Series(data=[1, 2, 3, 4, 5])]})
# dummy_prediction_forwarder = MockPredictionStorageProvider({"mock_data": [pd.Series(data=[1, 2, 3, 4, 5])]})


def _get_config():
    not_found = "Not found in environment variables"
    # fmt: off
    return {
        "executor":{
            "instance_count": 1,
        },
        "task_queue":{
            "type": "mock",
            "connection_string": "dummy",
            "security.protocol": "SASL_SSL",
            "ssl.ca.location": "/etc/ssl/certs/ca-certificates.crt",
            "sasl.mechanism": "PLAIN",
            "group.id": "1",
            "client.id": "executor",
            "request.timeout.ms": 10000,
            "session.timeout.ms": 10000,
            "default.topic.config": {
                "auto.offset.reset": "smallest"
            },
            "debug": "fetch",
            "topic": "latigo_topic",
            "enable.auto.commit": True,
            "auto.commit.interval.ms": 1000,
        },
        
        "sensor_data":{
            "type": "mock",
            "base_url": "dummy",
            "async": False,
            "auth":{
                "resource": "not set from env in executor_config.yaml",
                "tenant": "not set from env in executor_config.yaml",
                "authority_host_url": "not set from env in executor_config.yaml",
                "client_id": "not set from env in executor_config.yaml",
                "client_secret": "dummy",
            },
        },
        
        
        "prediction_storage":{
            "type": "mock",
            "base_url": "dummy",
            "async": False,
            "auth":{
                "resource": "not set from env in executor_config.yaml",
                "tenant": "not set from env in executor_config.yaml",
                "authority_host_url": "not set from env in executor_config.yaml",
                "client_id": "not set from env in executor_config.yaml",
                "client_secret": "dummy",
            },
        },
        
        
        "model_info":{
            "type": "mock",
            "connection_string": "dummy",
            "projects": ['project-1', 'project-2'],
            "target": None,
            "metadata": None,
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
            "auth":{
                "resource": "set from env",
                "tenant": "set from env",
                "authority_host_url": "set from env",
                "client_id": "set from env",
                "client_secret": "dummy",
            },
        },
        
        "predictor":{
            "type": "mock",
            "connection_string": "dummy",
            "target": None,
            "metadata": None,
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
            "auth":{
                "resource": "not set from env in executor_config.yaml",
                "tenant": "not set from env in executor_config.yaml",
                "authority_host_url": "not set from env in executor_config.yaml",
                "client_id": "not set from env in executor_config.yaml",
                "client_secret": "dummy",
            },
        },
    }
    # fmt: on


def test_fetch_task():
    pe = PredictionExecutor(config=_get_config())

    ret = pe._fetch_spec(project_name="project", model_name="model")
    logger.info(ret)
