from datetime import datetime
from io import StringIO
from typing import List
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from latigo.time_series_api import TimeSeriesAPIPredictionStorageProvider, TimeSeriesAPISensorDataProvider
from latigo.types import ModelTrainingPeriod, PredictionDataSet, PredictionDataSetMetadata, TimeRange, SensorDataSet


@pytest.fixture
def prediction_data() -> PredictionDataSet:
    model_training_period = ModelTrainingPeriod(
        train_start_date=datetime.fromisoformat("2020-02-01 00:00:00.000000+00:00"),
        train_end_date=datetime.fromisoformat("2020-04-01 00:00:00.000000+00:00"),
    )
    meta_data = PredictionDataSetMetadata(
        project_name="1903", model_name="model", revision="revision", model_training_period=model_training_period,
    )

    dataframe_data = StringIO(
        """
        start/  end/  model-input/1903.R1  model-input/1903.R2   model-output/1903.R1  model-output/1903.R2  confidence/
        2020-05-30T10:10:00Z  2020-05-30T10:10:00Z  2020-05-30T10:20:00Z  600.63  600.63  14.28  13.38  5.721942e+06
        2020-05-30T10:20:00Z  2020-05-30T10:20:00Z  2020-05-30T10:29:00Z  679.72  679.72  14.28  13.38  5.832050e+06
        """
    )

    indexes = []
    dataframe = pd.read_csv(dataframe_data, sep=r"\s+")
    for i, col in enumerate(dataframe.columns.values):
        indexes.append(tuple(col.split("/")))
    dataframe.columns = pd.MultiIndex.from_tuples(indexes)
    data_in_prediction = [("model_name", dataframe, [])]

    time_range = TimeRange(
        from_time=datetime.fromisoformat("2020-05-30 10:00:00.000000+00:00"),
        to_time=datetime.fromisoformat("2020-05-30 10:30:30.000000+00:00"),
    )

    return PredictionDataSet(data=data_in_prediction, meta_data=meta_data, time_range=time_range)


@pytest.fixture
@patch("latigo.time_series_api.client.get_auth_session", new=Mock())
def prediction_storage(config) -> TimeSeriesAPIPredictionStorageProvider:
    prediction_storage = TimeSeriesAPIPredictionStorageProvider(config["prediction_storage"])
    return prediction_storage


@pytest.fixture
def tag_metadata() -> dict:
    return {
        "data": {
            "items": [
                {
                    "id": "tag_id",
                    "name": "1903.R-29|model|model-output",
                    "description": "description",
                    "step": True,
                    "unit": None,
                    "assetId": None,
                    "facility": None,
                    "externalId": None,
                    "changedTime": "2020-03-30T13:21:32.400Z",
                    "createdTime": "2020-03-30T13:21:32.400Z",
                }
            ]
        }
    }


@pytest.fixture
@patch("latigo.time_series_api.client.get_auth_session", new=Mock())
def ts_api(config) -> TimeSeriesAPISensorDataProvider:
    return TimeSeriesAPISensorDataProvider(config["sensor_data"])


def get_meta_by_name_resp(tag_id: str, name: str):
    return {
        "data": {
            "items": [
                {
                    "id": tag_id,
                    "name": name,
                    "description": "Oljeeksp kjøling",
                    "step": False,
                    "unit": "°C",
                    "assetId": "GRA",
                    "facility": "1755",
                    "externalId": "GRA-49543",
                    "changedTime": "2020-09-25T10:00:00.000Z",
                    "createdTime": "2020-09-10T10:00:00.000Z",
                }
            ]
        }
    }


def fetch_data_for_multiple_ids_resp(tag_ids: List[str]):
    return [
        {"id": tag_id, "datapoints": [{"time": "2020-04-10T10:00:00.000Z", "value": 11.11, "status": 192}]}
        for tag_id in tag_ids
    ]


def make_sensor_data_set(from_time: datetime, to_time: datetime, tags_data: List[dict]) -> SensorDataSet:
    dataframes = []
    tag_names = ["0", "1", "2"]

    for tag_data in tags_data:
        tag_name = tag_names.pop(0)
        values = []
        indexes = []
        for point in tag_data["datapoints"]:
            values.append(point["value"])
            indexes.append(point["time"])

        datatime_index = pd.to_datetime(indexes, infer_datetime_format=True, utc=True)
        s = pd.Series(data=values, index=datatime_index, name=tag_name)
        dataframes.append(s)

    return SensorDataSet(time_range=TimeRange(from_time=from_time, to_time=to_time), data=dataframes)
