import typing
import logging
import requests
import pprint
from requests.exceptions import HTTPError
import pandas as pd

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

def _itemes_present(res:dict) -> bool:
    if not res:
        return False
    data=res.get('data', {})
    if not data:
        return False
    items=data.get('items', [])
    if not items:
        return False
    return True

def _id_in_data(res):
    if not res:
        return None
    data=res.get('data', {})
    if not data:
        return None
    items=data.get('items', [])
    if not items:
        return None
    item = items[0]
    if not item:
        return None
    return item.get('id', None)

def _get_auth_session(auth_config: dict):
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
        self.session = _get_auth_session(self.auth_config)

    def __init__(self, config: dict):
        self.config = config
        if not self.config:
            raise Exception("No config specified")
        self._parse_auth_config()
        self._parse_base_url()
        self.do_async = self.config.get("async", False)

    
    def _parse_request_json(self, res):
        try:
            res.raise_for_status()
            ret = res.json()
            ret["latigo-ok"] = True
            ret["latigo-error"] = None
            return ret, None
        except HTTPError as http_err:
            msg=f"Could not {res.request.method} @ {res.request.url}:\nHTTP error occurred: {http_err}"
            logger.error(msg)
            return {"latigo-ok": False, "latigo-error": msg}, msg
        except Exception as err:
            msg=f"Could not {res.request.method} @ {res.request.url}:\nOther error occurred: {err}"
            logger.error(msg)
            raise err
            return {"latigo-ok": False, "latigo-error": msg}, msg

    def _fetch_data(self, id: str, time_range: TimeRange) -> typing.Optional[dict]:
        url = f"{self.base_url}/{id}/data?startTime={time_range.rfc3339_from()}&endTime={time_range.rfc3339_to()}&limit=100000&includeOutsidePoints=true"
        res = self.session.get(url)
        return self._parse_request_json(res)
    
    def _get_id_by_name(self, name:str) -> bool:
        body={'name': name}
        logger.info("Getting:")
        logger.info(pprint.pformat(body))
        res = self.session.get(self.base_url, params=body)
        obj, err=self._parse_request_json(res)
        logger.info(pprint.pformat(obj))
        return obj
    
    
    def _id_exists_for_name(self, name:str):
        res = self._get_id_by_name(name)
        return _itemes_present(res)
    
    def _create_id(self, name:str, description:str="", unit:str="", asset_id:str="", external_id:str=""):
        body={
                "name": name,
                "description": description,
                "step": True,
                "unit": unit,
                "assetId": asset_id,
                "externalId": external_id
        }
        logger.info("Posting:")
        logger.info(pprint.pformat(body))
        res = self.session.post(self.base_url, json=body, params=None)
        obj, err=self._parse_request_json(res)
        logger.info(pprint.pformat(obj))
        return obj

    def _create_id_if_not_exists(self, name:str, description:str="", unit:str="", asset_id:str="", external_id:str=""):
        meta = self._get_id_by_name(name)
        if not _itemes_present(meta):
            return self._create_id(name, description, unit, asset_id, external_id)
        return meta


    def _store_data_for_id(self, id:str, data:typing.Iterable[typing.Tuple[str, pd.DataFrame, typing.List[str]]]):
        
        



        datapoints=[]
        datapoints.append(
        {
            "time": "2019-04-12T08:13:44.154Z",
            "value": 0.5,
            "status": 2147483843
        })
        body={
          "datapoints": datapoints
        }
        url=f"{self.base_url}/{id}/data"
        res = self.session.post(url, json=body, params=None)
        return self._parse_request_json(res)

    def _store_data_by_id(self, id: str, data: dict):
        url = f"{self.base_url}/timeseries/v1.5/{id}/data?async={self.do_async}"
        res = self.session.post(url, data=data)
        return self._parse_request_json(res)


class TimeSeriesAPISensorDataProvider(TimeSeriesAPIClient, SensorDataProviderInterface):
    def __init__(self, config: dict):
        super().__init__(config)
        self._parse_auth_config()
        self._parse_base_url()



    def get_data_for_range(self, spec: SensorDataSpec, time_range: TimeRange) -> SensorData:
        """
        return the actual data as per the range specified
        """
        meta = self._look_up_meta()
        id = "test_id"
        ts = self._fetch_data(id, time_range)
        if not ts.get('latigo-ok', False):
            return None, ts.get('latigo-error', 'Unknon failure')
        data = transform_from_timeseries_to_gordo(ts)
        sensor_data = SensorData(time_range=time_range, data=data)
        return sensor_data, None




class TimeSeriesAPIPredictionStorageProvider(TimeSeriesAPIClient, PredictionStorageProviderInterface):
    def __init__(self, config: dict):
        super().__init__(config)

    def put_predictions(self, prediction_data: PredictionData):
        """
        Store prediction data in time series api
        """
        name="pop"
        description="test for latigo ved lennart rolland"
        unit="Kg"
        asset_id="test_asset_id"
        external_id="test_external_id"
        data=prediction_data.data
        meta=self._create_id_if_not_exists(name=name, description=description, unit=unit, asset_id=asset_id, external_id=external_id )
        logger.info(f"GOT META: {meta}")
        id=_id_in_data(meta)
        if not id:
            raise Exception(f"No ID returned from Time Series API for {name}")
        obj, err=self._store_data_for_id(id=id, data=data)
        #logger.info(pprint.pformat(obj))
        return obj
