import logging

logger = logging.getLogger(__name__)


class ModelInfoProviderInterface:
    def get_model_info(self, model_name: str) -> dict:
        """
        Return any information about a named prediction
        """
        pass

    def get_models(self, filter: dict) -> list:
        """
        Return a list of predictions matching the given filter.
        """
        pass


class MockModelInfoProvider(ModelInfoProviderInterface):
    def __init__(self, config: dict):
        self.config = config

    def get_model_info(self, model_name: str):
        """
        Return any information about a named prediction
        """
        return {}

    def get_models(self, filter: dict):
        """
        Return a list of predictions matching the given filter.
        """
        return []


class DevNullModelInfoProvider(ModelInfoProviderInterface):
    def __init__(self, config: dict):
        pass

    def get_model_info(self, model_name: str):
        """
        Return any information about a named prediction
        """
        return {}

    def get_models(self, filter: dict):
        """
        Return a list of predictions matching the given filter.
        """
        return []
