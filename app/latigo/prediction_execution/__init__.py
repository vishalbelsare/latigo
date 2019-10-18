from datetime import datetime
import random
import typing
import numpy as np
import pandas as pd
from pprint import pprint
from dataclasses import dataclass

from latigo.sensor_data import SensorData, PredictionData


class PredictionExecutionProviderInterface:
    def execute_prediction(self, prediction_name: str, data: SensorData) -> PredictionData:
        """
        Train and/or run data through a given model
        """


class MockPredictionExecutionProvider(PredictionExecutionProviderInterface):
    def execute_prediction(self, prediction_name: str, data: SensorData) -> PredictionData:
        """
        Testing mock prediction execution provider
        """
        data = PredictionData(name=prediction_name, time_range=data.time_range, result=[])
        return data


class DevNullPredictionExecutionProvider(PredictionExecutionProviderInterface):
    def execute_prediction(self, prediction_name: str, data: SensorData) -> PredictionData:
        """
        Dummy no-op prediction execution provider
        """
        data = PredictionData(name=prediction_name, time_range=data.time_range, result=[])
        return data
