from datetime import datetime
import random
import typing
import numpy as np
import pandas as pd
from pprint import pprint
from dataclasses import dataclass

from latigo.types import SensorDataSet, PredictionDataSet, ModelTrainingPeriod


class PredictionExecutionProviderInterface:
    def execute_prediction(
        self,
        project_name: str,
        model_name: str,
        sensor_data: SensorDataSet,
        revision: str,
        model_training_period: ModelTrainingPeriod,
    ) -> PredictionDataSet:
        """
        Train and/or run data through a given model
        """
        raise NotImplementedError()


class MockPredictionExecutionProvider(PredictionExecutionProviderInterface):
    def __init__(self, sensor_data, prediction_storage, config: dict):
        self.config = config

    def execute_prediction(
        self,
        project_name: str,
        model_name: str,
        sensor_data: SensorDataSet,
        revision: str,
        model_training_period: ModelTrainingPeriod,
    ) -> PredictionDataSet:
        """
        Testing mock prediction execution provider
        """
        # prediction_data = PredictionDataSet(name=model_name, time_range=sensor_data.time_range, asset_id=asset_id, data=sensor_data, unit=unit)
        # return prediction_data
        raise NotImplementedError("HALP!")
        return None


class DevNullPredictionExecutionProvider(PredictionExecutionProviderInterface):
    def __init__(self, sensor_data, prediction_storage, config: dict):
        self.config = config

    def execute_prediction(
        self,
        project_name: str,
        model_name: str,
        sensor_data: SensorDataSet,
        revision: str,
        model_training_period: ModelTrainingPeriod,
    ) -> PredictionDataSet:
        """
        Dummy no-op prediction execution provider
        """
        # prediction_data = PredictionDataSet(name=model_name, time_range=sensor_data.time_range, asset_id=asset_id, data=sensor_data, unit=unit)
        # return prediction_data
        raise NotImplementedError("HALP!")
        return None


def prediction_execution_provider_factory(
    sensor_data_provider, prediction_storage_provider, prediction_execution_config
):
    prediction_execution_type = prediction_execution_config.get("type", None)
    prediction_execution = None
    if "gordo" == prediction_execution_type:
        from latigo.gordo import GordoPredictionExecutionProvider

        prediction_execution = GordoPredictionExecutionProvider(
            sensor_data_provider,
            prediction_storage_provider,
            prediction_execution_config,
        )
    elif "mock" == prediction_execution_type:
        prediction_execution = MockPredictionExecutionProvider(
            sensor_data_provider,
            prediction_storage_provider,
            prediction_execution_config,
        )
    else:
        prediction_execution = DevNullPredictionExecutionProvider(
            sensor_data_provider,
            prediction_storage_provider,
            prediction_execution_config,
        )
    return prediction_execution
