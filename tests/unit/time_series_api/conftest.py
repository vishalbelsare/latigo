from datetime import datetime
from io import StringIO
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from latigo.time_series_api import TimeSeriesAPIPredictionStorageProvider
from latigo.types import ModelTrainingPeriod, PredictionDataSet, PredictionDataSetMetadata, TimeRange


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
