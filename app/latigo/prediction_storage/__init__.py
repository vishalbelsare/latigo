

class PredictionStorageProviderInterface:
    def put_predictions(self, predictions:PredictionData) :
        """
        Store the predictions
        """
        pass

class MockPredictionStorageProvider(PredictionStorageProviderInterface):

    def put_predictions(self, predictions:PredictionData) :
        """
        Store the predictions
        """
        pass

