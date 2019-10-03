import logging

from latigo.sensor_data import *


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
        self.logger = logging.getLogger(__class__.__name__)
        self.do_log = do_log

    def put_predictions(self, predictions: PredictionData):
        """
        Don't store the predictions on purpose
        """
        if self.do_log:
            self.logger.info(f'Deleting predictions: {predictions}')
        pass
