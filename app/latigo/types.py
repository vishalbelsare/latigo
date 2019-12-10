import pandas as pd
import typing
from datetime import datetime, timedelta
from collections import namedtuple
from dataclasses import dataclass
from dataclasses_json import dataclass_json, DataClassJsonMixin

from latigo.utils import rfc3339_from_datetime


@dataclass
class Task(DataClassJsonMixin):
    project_name: str = "unknown"
    model_name: str = "unknown"
    from_time: datetime = datetime.now() - timedelta(0, 20)
    to_time: datetime = datetime.now()


@dataclass
class TimeRange:

    from_time: datetime
    to_time: datetime

    def rfc3339_from(self):
        return rfc3339_from_datetime(self.from_time)

    def rfc3339_to(self):
        return rfc3339_from_datetime(self.to_time)

    def __str__(self):
        return f"TimeRange({self.from_time} -> {self.to_time})"


LatigoSensorTag = namedtuple("LatigoSensorTag", ["name", "asset"])


@dataclass
class SensorDataSpec:
    tag_list: typing.List[LatigoSensorTag]


@dataclass
class SensorData:
    name: str
    unit: str
    asset_id: str
    time_range: TimeRange
    data: typing.Iterable[pd.Series]

    def __str__(self):
        return f"SensorData(time_range={self.time_range}, name={self.name}, unit={self.unit}, asset_id={self.asset_id}, data={len(self.data)})"

    def ok(self):
        return bool(self.time_range) and bool(self.data) and bool(self.name) and bool(self.asset_id)


@dataclass
class PredictionData:
    name: str
    unit: str
    asset_id: str
    time_range: TimeRange
    data: typing.Iterable[typing.Tuple[str, pd.DataFrame, typing.List[str]]]

    def __str__(self):
        return f"PredictionData({self.time_range}, name={self.name}, unit={self.unit}, asset_id={self.asset_id}, data={len(self.data)})"

    def ok(self):
        return bool(self.time_range) and bool(self.data) and bool(self.name) and bool(self.asset_id)
