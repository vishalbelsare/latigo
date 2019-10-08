from datetime import datetime
import random
import typing
import numpy as np
import pandas as pd
from pprint import pprint
from dataclasses import dataclass

from latigo.sensor_data import SensorData, PredictionData
from latigo.utils import parse_event_hub_connection_string
from latigo.event_hub.receive import EventReceiveClient


@dataclass
class PredictionInfo:
    name: str


class PredictionInformationProviderInterface:
    def get_prediction_info(self, prediction_name: str) -> PredictionInfo:
        """
        return any information about a named prediction
        """

    def get_predictions(self, selector: dict):
        """
        return a list of predictions matching the given selector.
        """


class MockPredictionInformationProvider(PredictionInformationProviderInterface):
    def get_prediction_info(self, prediction_name: str) -> PredictionInfo:
        """
        return any information about a named prediction
        """
        pi = PredictionInfo(name=prediction_name)
        return pi

    def get_predictions(self, selector: dict) -> typing.List[PredictionInfo]:
        """
        return a list of predictions matching the given selector.
        """
        predictions_list = []
        for i in range(3):
            pi = PredictionInfo(f"pred_{i}")
            predictions_list.append(pi)
        return predictions_list


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
