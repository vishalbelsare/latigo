#!/usr/bin/env python
import pandas as pd
import typing
import logging
from datetime import datetime, timedelta
from collections import namedtuple
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, DataClassJsonMixin
from gordo.machine.dataset.sensor_tag import SensorTag

from latigo.utils import rfc3339_from_datetime
from latigo.intermediate import IntermediateFormat


logger = logging.getLogger(__name__)


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
        return f"TimeRange({rfc3339_from_datetime(self.from_time)} -> {rfc3339_from_datetime(self.to_time)})"


LatigoSensorTag = namedtuple("LatigoSensorTag", ["name", "asset"])


@dataclass
class SensorDataSpec:
    tag_list: typing.List[LatigoSensorTag]


@dataclass
class SensorDataSet:
    time_range: TimeRange
    data: typing.Optional[IntermediateFormat]
    meta_data: typing.Dict = field(default_factory=dict)

    def ok(self):
        # logger.warning(f"TIME:{self.time_range}")
        # logger.warning(f"META:{self.meta_data}")
        # logger.warning(f"DATA:{self.data}")
        if not self.data:
            return False
        if len(self.data) < 1:
            return False
        return True

    def __str__(self):
        return f"SensorDataSet(time_range={self.time_range}, data={self.data}, meta_data={self.meta_data})"


@dataclass
class PredictionDataSet:
    time_range: TimeRange
    data: typing.Optional[typing.Any]
    meta_data: typing.Dict = field(default_factory=dict)

    def ok(self):
        return True

    def __str__(self):
        return f"PredictionDataSet(time_range={self.time_range}, data={self.data}, meta_data={self.meta_data})"


############# ATTIC


@dataclass
class PredictionDataSeries:
    name: str
    unit: str
    asset_id: str
    time_range: TimeRange
    data: typing.Iterable[typing.Tuple[str, pd.DataFrame, typing.List[str]]]

    def __str__(self):
        return f"PredictionData({self.time_range}, name={self.name}, unit={self.unit}, asset_id={self.asset_id}, data={len(self.data)})"

    def ok(self):
        return (
            bool(self.time_range)
            and bool(self.data)
            and bool(self.name)
            and bool(self.asset_id)
        )


@dataclass
class SensorDataSeries:
    tag_name: str
    asset_id: str
    unit: str
    time_range: TimeRange
    data: typing.Iterable[pd.Series]
