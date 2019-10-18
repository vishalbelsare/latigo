from os import environ
from latigo.gordo import GordoModelInfoProvider

class TestGordoClient:
    
    def test_model_info(self):
        config={
            "project": '1130-gordo-tilstandomatic',
            "target": None,
            "host": "localhost",
            "port": "8888",
            "scheme": "http",
            "gordo_version": "v0",
            "metadata": None,
            "data_provider": None,
            "prediction_forwarder": None,
            "batch_size": 1000,
            "parallelism": 10,
            "forward_resampled_sensors": False,
            "ignore_unhealthy_targets": True,
            "n_retries": 5,
            "data_provider": None,
            "prediction_forwarder": None
        }
        gordo_model_info_provider = GordoModelInfoProvider(config)
        models=gordo_model_info_provider.get_models()
