import typing
import logging
import requests
from requests.exceptions import HTTPError

from latigo.types import Task, SensorDataSpec, SensorData, TimeRange, PredictionData
from latigo.sensor_data import SensorDataProviderInterface
from latigo.prediction_storage import PredictionStorageProviderInterface
import latigo.utils
from latigo.auth import create_auth_session

logger = logging.getLogger(__name__)

timeseries_client_auth_session: typing.Optional[requests.Session] = None


def transform_from_timeseries_to_gordo(data: typing.Optional[dict]):
    return data


def transform_from_gordo_to_timeseries(data: typing.Optional[dict]):
    return data


def get_auth_session(auth_config: dict):
    global timeseries_client_auth_session
    if not timeseries_client_auth_session:
        # logger.info("CREATING SESSION:")
        timeseries_client_auth_session = create_auth_session(auth_config)
    return timeseries_client_auth_session


class TimeSeriesAPIClient:
    def _parse_base_url(self):
        if "base_url" in self.config:
            self.base_url = self.config.pop("base_url")
            parts = latigo.utils.parse_time_series_api_base_url(self.base_url)
            if parts:
                self.update(parts)

    def _parse_auth_config(self):
        self.auth_config = self.config.get("auth", dict())
        self.session = get_auth_session(self.auth_config)

    def __init__(self, config: dict):
        self.config = config
        if not self.config:
            raise Exception("No time_series_config specified")
        self._parse_auth_config()
        self._parse_base_url()
        self.do_async = self.config.get("async", False)

    def _fetch_data(self, id: str, time_range: TimeRange) -> typing.Optional[dict]:
        url = f"{self.base_url}/timeseries/v1.5/{id}/data?startTime={time_range.rfc3339_from()}&endTime={time_range.rfc3339_to()}&limit=100000&includeOutsidePoints=true"
        res = self.session.get(url)
        try:
            res.raise_for_status()
            ret = res.json()
            ret["latigo-ok"] = True
            return ret
        except HTTPError as http_err:
            logger.warning(f"Could not fetch data from {url}: HTTP error occurred: {http_err}")
            return {"latigo-ok": False}
        except Exception as err:
            logger.warning(f"Could not fetch data from {url}: Other error occurred: {err}")
            return {"latigo-ok": False}

    def _store_data(self, id: str, data: dict):
        url = f"{self.base_url}/timeseries/v1.5/{id}/data?async={self.do_async}"
        res = self.session.post(url, data=data)
        if res:
            ret = res.json()
            ret["latigo-ok"] = True
            return ret
        else:
            logger.warning(f"Could not store data to {url}")
            return {"latigo-ok": False}


class TimeSeriesAPISensorDataProvider(TimeSeriesAPIClient, SensorDataProviderInterface):
    def __init__(self, config: dict):
        self.config = config
        if not self.config:
            raise Exception("No time_series_config specified")
        self._parse_auth_config()
        self._parse_base_url()

    def _look_up_meta(self):
        pass

    def get_data_for_range(self, spec: SensorDataSpec, time_range: TimeRange) -> SensorData:
        """
        return the actual data as per the range specified
        """
        meta = self._look_up_meta()
        id = "test_id"
        ts = self._fetch_data(id, time_range)
        data = transform_from_timeseries_to_gordo(ts)
        sensor_data = SensorData(time_range=time_range, data=data)
        return sensor_data


class TimeSeriesAPIPredictionStorageProvider(TimeSeriesAPIClient, PredictionStorageProviderInterface):
    def __init__(self, config: dict):
        self.config = config

    def put_predictions(self, prediction_data: PredictionData):
        """
        Store prediction data in time series api
        """
        if self.config.get("do_log", False):
            logger.info(f"Deleting prediction data: {prediction_data}")
        pass
