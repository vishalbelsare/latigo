from dataclasses import dataclass
from datetime import datetime, timedelta
import pandas as pd
import typing


@dataclass
class TimeRange:

    from_time: datetime
    to_time: datetime

    def __str__(self):
        return f"TimeRange({self.from_time} -> {self.to_time})"


@dataclass
class SensorData:

    time_range: TimeRange
    data: typing.Iterable[pd.Series]

    def __str__(self):
        return f"PredictionData({self.time_range})"


@dataclass
class PredictionData:
    name: str
    time_range: TimeRange
    data: typing.Iterable[typing.Tuple[str, pd.DataFrame, typing.List[str]]]

    def __str__(self):
        return f"PredictionData({self.time_range}, result={len(self.result)})"


def sensor_data_provider_factory(sensor_data_provider_config):
    sensor_data_provider_type = sensor_data_provider_config.get("type", None)
    sensor_data_provider = None
    if "influx" == sensor_data_provider_type:
        from latigo.sensor_data.sensor_data import InfluxSensorDataProvider

        sensor_data_provider = InfluxSensorDataProvider(sensor_data_provider_config)
    elif "influx" == sensor_data_provider_type:
        from latigo.sensor_data.sensor_data import MockSensorDataProvider

        sensor_data_provider = MockSensorDataProvider(sensor_data_provider_config)
    else:
        from latigo.sensor_data.sensor_data import DevNullSensorDataProvider

        sensor_data_provider = DevNullSensorDataProvider(sensor_data_provider_config)
    return sensor_data_provider
