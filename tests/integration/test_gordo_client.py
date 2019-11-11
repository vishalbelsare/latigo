from os import environ
from latigo.gordo import GordoModelInfoProvider


class TestGordoClient:
    def test_model_info(self):
        if environ.get("LATIGO_GORDO_CLIENT_SECRET", False):
            # fmt: off
            config = {
                "project": "1130-gordo-tilstandomatic",
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
                "prediction_forwarder": None,
                "auth":{
                    "resource": environ.get("LATIGO_GORDO_RESOURCE", "NOT SET"),
                    "tenant" : environ.get("LATIGO_GORDO_TENANT", "NOT SET"),
                    "authority_host_url" : environ.get("LATIGO_GORDO_AUTH_HOST_URL", "NOT SET"),
                    "client_id" : environ.get("LATIGO_GORDO_CLIENT_ID", "NOT SET"),
                    "client_secret" : environ.get("LATIGO_GORDO_CLIENT_SECRET", "NOT SET"),
                },
            }
            # fmt: on
            gordo_model_info_provider = GordoModelInfoProvider(config)
            models = gordo_model_info_provider.get_models()
