import pandas as pd
import typing
from datetime import datetime, timedelta
from os import environ
from collections import namedtuple
from latigo.time_series_api import TimeSeriesAPIPredictionStorageProvider, TimeSeriesAPISensorDataProvider
from latigo.types import PredictionData, TimeRange, SensorDataSpec


def _get_config():
    not_found = "Not found in environment variables"
    # fmt: off
    return {
        "type": "time_series_api",
        "base_url": environ.get("LATIGO_TIME_SERIES_BASE_URL", not_found),
        "async": False,
        "auth": {
            "resource": environ.get("LATIGO_TIME_SERIES_RESOURCE", not_found),
            "tenant": environ.get("LATIGO_TIME_SERIES_TENANT", not_found),
            "authority_host_url": environ.get("LATIGO_TIME_SERIES_AUTH_HOST_URL", not_found),
            "client_id": environ.get("LATIGO_TIME_SERIES_CLIENT_ID", not_found),
            "client_secret": environ.get("LATIGO_TIME_SERIES_CLIENT_SECRET", not_found)
        }
    }
    # fmt: on

name: str="latigo_integration_test"
from_time:datetime=datetime.strptime('2019-11-01 13:33:37', '%Y-%m-%d %H:%M:%S')
to_time:datetime=datetime.strptime('2019-11-01 14:20:59', '%Y-%m-%d %H:%M:%S')
time_range: TimeRange = TimeRange(from_time, to_time)

tag_list = [("tag_name_1", "tag_asset_1"), ("tag_name_2", "tag_asset_2") ]
spec:SensorDataSpec= SensorDataSpec(tag_list = tag_list)


data: typing.Iterable[typing.Tuple[str, pd.DataFrame, typing.List[str]]] = []

def test_time_series_api_write():
    prediction_storage_provider = TimeSeriesAPIPredictionStorageProvider(_get_config())
    prediction_data = PredictionData(name = name, time_range = time_range, data = data)
    prediction_storage_provider.put_predictions(prediction_data)

def test_time_series_api_read():
    sensor_data_provider = TimeSeriesAPISensorDataProvider(_get_config())
    sensor_data = sensor_data_provider.get_data_for_range(spec=spec, time_range=time_range)

