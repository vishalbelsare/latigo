from datetime import datetime
import random
import typing
import numpy as np
import pandas as pd
from pprint import pprint
from dataclasses import dataclass

from latigo.types import SensorData, PredictionData


class PredictionExecutionProviderInterface:
    def execute_prediction(self, project_name: str, model_name: str, asset_id: str, sensor_data: SensorData, unit: str = None) -> PredictionData:
        """
        Train and/or run data through a given model
        """


class MockPredictionExecutionProvider(PredictionExecutionProviderInterface):
    def __init__(self, sensor_data, prediction_storage, config: dict):
        self.config = config

    def execute_prediction(self, project_name: str, model_name: str, asset_id: str, sensor_data: SensorData, unit: str = None) -> PredictionData:
        """
        Testing mock prediction execution provider
        """
        prediction_data = PredictionData(name=model_name, time_range=sensor_data.time_range, asset_id=asset_id, data=sensor_data, unit=unit)
        return prediction_data


class DevNullPredictionExecutionProvider(PredictionExecutionProviderInterface):
    def __init__(self, sensor_data, prediction_storage, config: dict):
        self.config = config

    def execute_prediction(self, project_name: str, model_name: str, asset_id: str, sensor_data: SensorData, unit: str = None) -> PredictionData:
        """
        Dummy no-op prediction execution provider
        """
        prediction_data = PredictionData(name=model_name, time_range=sensor_data.time_range, asset_id=asset_id, data=sensor_data, unit=unit)
        return prediction_data


def prediction_execution_provider_factory(sensor_data_provider, prediction_storage_provider, prediction_execution_config):
    prediction_execution_type = prediction_execution_config.get("type", None)
    prediction_execution = None
    if "gordo" == prediction_execution_type:
        from latigo.gordo import GordoPredictionExecutionProvider

        prediction_execution = GordoPredictionExecutionProvider(sensor_data_provider, prediction_storage_provider, prediction_execution_config)
    elif "mock" == prediction_execution_type:
        prediction_execution = MockPredictionExecutionProvider(sensor_data_provider, prediction_storage_provider, prediction_execution_config)
    else:
        prediction_execution = DevNullPredictionExecutionProvider(sensor_data_provider, prediction_storage_provider, prediction_execution_config)
    return prediction_execution
