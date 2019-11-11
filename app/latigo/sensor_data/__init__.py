from dataclasses import dataclass
from datetime import datetime, timedelta
import pandas as pd
import typing
import latigo.utils


from latigo.types import SensorData, TimeRange, SensorDataSpec


class SensorDataProviderInterface:
    def get_data_for_range(self, spec: SensorDataSpec, time_range: TimeRange) -> SensorData:
        """
        return the actual data as per the range specified
        """
        pass


class MockSensorDataProvider(SensorDataProviderInterface):
    def __init__(self, config: dict):
        self.config = config

    def get_data_for_range(self, spec: SensorDataSpec, time_range: TimeRange) -> SensorData:
        """
        return the actual data as per the range specified
        """
        data = SensorData(time_range=time_range, data=[])
        return data


class DevNullSensorDataProvider(SensorDataProviderInterface):
    def __init__(self, config: dict):
        self.config = config

    def get_data_for_range(self, spec: SensorDataSpec, time_range: TimeRange) -> SensorData:
        """
        return the actual data as per the range specified
        """
        data = SensorData(time_range=time_range, data=[])
        return data


def sensor_data_provider_factory(sensor_data_provider_config):
    sensor_data_provider_type = sensor_data_provider_config.get("type", None)
    sensor_data_provider = None

    if "time_series_api" == sensor_data_provider_type:
        from latigo.time_series_api import TimeSeriesAPISensorDataProvider

        sensor_data_provider = TimeSeriesAPISensorDataProvider(sensor_data_provider_config)
    elif "mock" == sensor_data_provider_type:
        sensor_data_provider = MockSensorDataProvider(sensor_data_provider_config)
    else:
        sensor_data_provider = DevNullSensorDataProvider(sensor_data_provider_config)
    return sensor_data_provider
