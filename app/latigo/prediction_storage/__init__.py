from latigo.sensor_data import PredictionData
import logging

logger = logging.getLogger(__name__)


class PredictionStorageProviderInterface:
    def put_predictions(self, predictions: PredictionData):
        """
        Store the predictions
        """
        pass


class MockPredictionStorageProvider(PredictionStorageProviderInterface):

    def put_predictions(self, predictions: PredictionData):
        """
        Store the predictions
        """
        pass


class DevNullPredictionStorageProvider(PredictionStorageProviderInterface):

    def __init__(self, do_log: bool = False):
        self.do_log = do_log

    def put_predictions(self, predictions: PredictionData):
        """
        Don't store the predictions on purpose
        """
        if self.do_log:
            logger.info(f'Deleting predictions: {predictions}')
        pass
