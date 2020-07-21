#!/usr/bin/env python
import logging
import typing
from collections import namedtuple
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd
from dataclasses_json import DataClassJsonMixin

from latigo.utils import datetime_to_utc_as_str, rfc3339_from_datetime

logger = logging.getLogger(__name__)


@dataclass
class Task(DataClassJsonMixin):
    project_name: str
    model_name: str
    from_time: datetime
    to_time: datetime

    def __str__(self):
        return (
            f"'model: {self.project_name}.{self.model_name}', prediction: from '{self.from_time}' to '{self.to_time}'"
        )


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
    data: typing.List[pd.Series]
    meta_data: typing.Dict = field(default_factory=dict)

    def __eq__(self, other):
        if self.time_range != other.time_range:
            return False
        if self.meta_data != other.meta_data:
            return False
        if len(self.data) != len(other.data):
            return False
        if not all(s1.equals(s2) for s1, s2 in zip(self.data, other.data)):
            return False
        return True

    def ok(self):
        if not self.data:
            return False
        if len(self.data) < 1:
            return False
        return True

    def __str__(self):
        return f"SensorDataSet(time_range={self.time_range}, data={self.data}, meta_data={self.meta_data})"

    @staticmethod
    def to_gordo_dataframe(
        data: typing.List[typing.Dict[str, typing.Any]], prediction_start_date: datetime, prediction_end_date: datetime
    ) -> typing.List[pd.Series]:
        """Format data for the DataFrames as Gordo required for the predictions.

        This function will filter incoming data and skip that is out of prediction time period.

        Args:
            data: taken from Time Series API income-tag`s data for making predictions on.
            prediction_start_date: start time of the prediction data.
            prediction_end_date: end time of the prediction data.

        Return:
            DataFrames for predictions (might be filtered).
        """
        dataframes: typing.List = []
        start_date = datetime_to_utc_as_str(prediction_start_date)
        end_date = datetime_to_utc_as_str(prediction_end_date)

        for tag_data in data:
            values = []
            index = []
            datapoints = tag_data["datapoints"]
            tag_name = tag_data["name"]

            for point in datapoints:
                point_time = point["time"]
                point_value = point["value"]

                # skip data points that are out of prediction time range.
                if start_date > point_time or point_time > end_date:
                    logger.error(
                        f"Skipped value before sending for prediction '{point_value}' with time {point_time}. "
                        f"From {start_date} to {end_date}. Tag {tag_name}"
                    )
                    continue
                values.append(point_value)
                index.append(point_time)

            index = pd.to_datetime(index, infer_datetime_format=True, utc=True)
            s = pd.Series(data=values, index=index, name=tag_name)
            dataframes.append(s)
        return dataframes


class ModelTrainingPeriod(typing.NamedTuple):
    """Training period of the model that is in the yaml file (not the period of the prediction)."""

    train_start_date: datetime
    train_end_date: datetime


@dataclass
class PredictionDataSetMetadata:
    """Metadata of prediction that was made by Gordo.

    Dataclass attributes:
        project_name: name of the project.
        model_name: name of the model.
        revision (optional): revision(version) of the entities that were used in the prediction.
        model_start_training: datetime = None

    """

    project_name: str
    model_name: str
    model_training_period: ModelTrainingPeriod
    revision: str = None

    def __post_init__(self):
        if not self.project_name or not self.model_name:
            raise ValueError("project_name and model_name can not be empty or None.")


@dataclass
class PredictionDataSet:
    time_range: TimeRange
    data: typing.Optional[typing.Any]
    meta_data: PredictionDataSetMetadata

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
        return bool(self.time_range) and bool(self.data) and bool(self.name) and bool(self.asset_id)


@dataclass
class SensorDataSeries:
    tag_name: str
    asset_id: str
    unit: str
    time_range: TimeRange
    data: typing.Iterable[pd.Series]
