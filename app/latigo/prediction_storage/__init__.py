import pprint
from latigo.types import PredictionDataSet
import logging

logger = logging.getLogger(__name__)


class PredictionStorageProviderInterface:
    def put_predictions(self, prediction_data: PredictionDataSet):
        """
        Store the prediction data
        """
        raise NotImplementedError()


class MockPredictionStorageProvider(PredictionStorageProviderInterface):
    def __init__(self, config: dict):
        self.config = config

    def put_predictions(self, prediction_data: PredictionDataSet):
        """
        Store the prediction data
        """
        logger.info("MOCK STORING PREDICTIONS:")
        logger.info(pprint.pformat(prediction_data))


class DevNullPredictionStorageProvider(PredictionStorageProviderInterface):
    def __init__(self, config: dict):
        self.config = config

    def put_predictions(self, prediction_data: PredictionDataSet):
        """
        Don't store the prediction data on purpose
        """
        if self.config.get("do_log", False):
            logger.info(f"Deleting prediction data: {prediction_data}")
        pass


def prediction_storage_provider_factory(prediction_storage_provider_config):
    prediction_storage_provider_type = prediction_storage_provider_config.get(
        "type", None
    )
    prediction_storage_provider = None

    if "time_series_api" == prediction_storage_provider_type:
        from latigo.time_series_api import TimeSeriesAPIPredictionStorageProvider

        prediction_storage_provider = TimeSeriesAPIPredictionStorageProvider(
            prediction_storage_provider_config
        )

    elif "influx" == prediction_storage_provider_type:
        from latigo.prediction_storage_provider import InfluxPredictionStorageProvider

        prediction_storage_provider = InfluxPredictionStorageProvider(
            prediction_storage_provider_config
        )
    elif "mock" == prediction_storage_provider_type:
        prediction_storage_provider = MockPredictionStorageProvider(
            prediction_storage_provider_config
        )
    else:
        prediction_storage_provider = DevNullPredictionStorageProvider(
            prediction_storage_provider_config
        )
    return prediction_storage_provider
