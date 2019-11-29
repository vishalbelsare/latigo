import typing
import logging
import requests
import pprint
from requests.exceptions import HTTPError
import pandas as pd
import urllib.parse

from latigo.types import Task, SensorDataSpec, SensorData, TimeRange, PredictionData, LatigoSensorTag
from latigo.sensor_data import SensorDataProviderInterface
from latigo.prediction_storage import PredictionStorageProviderInterface
import latigo.utils
from latigo.auth import create_auth_session

logger = logging.getLogger(__name__)

timeseries_client_auth_session: typing.Optional[requests.Session] = None

"""
Time series format:
    
    data=[
        {
        'data': {
            'items': [
                {
                    'id': '9d1163a3-5ba8-454e-aca8-f087557252cf',
                    'name': 'GRA-FOI -13-0979.PV',
                    'unit': 'Sm³/h',
                    'datapoints': [
                        {
                            'time': '2019-06-10T21:00:07.616Z',
                            'value': 0.0647279506972897,
                            'status': 192
                        }
                     ]
                 }
             ]
         },
         'latigo-ok': True,
         'latigo-error': None
     }
    ]
"""


def transform_from_timeseries_to_gordo(items: typing.List):
    if not items:
        return None
    tag_names = []
    # Collect tag names in a list
    for i in range(len(items)):
        data = items[i]
        tag_name = data.get("name", None)
        # logger.info(f"TESTING DATA {i}:\n____DATA={data}\n_____TAG_NAME=({tag_name})")
        if not tag_name:
            continue
        tag_names.append(tag_name)
    tag_names_map = {}
    tag_names_data: typing.Dict[str, typing.List] = {}
    index = 0
    # Create tag name to index map
    for tag_name in tag_names:
        tag_names_map[tag_name] = index
        tag_names_data[tag_name] = []
        index += 1
    # Pack time series data by tag_name
    for i in range(len(items)):
        data = items[i]
        tag_name = data.get("name", None)
        if not tag_name:
            continue
        datapoints = data.get("datapoints", None)
        for datapoint in datapoints:
            if not datapoint:
                continue
            value = datapoint.get("value", None)
            if not value:
                continue
            if tag_name in tag_names_data:
                tag_names_data[tag_name].append(value)
    gordo_data = []
    # Caluclate minimum series length:
    BIG = 100000000
    ag_len = BIG
    for tag_name in tag_names:
        l = len(tag_names_data[tag_name])
        ag_len = l if l < ag_len else ag_len
    if BIG == ag_len:
        ag_len = 0
    tl_len = len(tag_names)
    # logger.info(f"AGLEN: {ag_len} TLLEN {tl_len}")
    # Create integer indexed gordo data
    for i in range(ag_len):
        line = []
        for j in range(tl_len):
            tag_name = tag_names[j]
            line.append(tag_names_data[tag_name][i])
        gordo_data.append(line)
    # logger.info(f"tagnames: {tag_names} tagmap {tag_names_map} tagdata {tag_names_data}")
    return {"X": gordo_data}


def transform_from_gordo_to_timeseries(data: typing.Optional[dict]):
    if not data:
        return None
    return data


def _itemes_present(res: dict) -> bool:
    if not res:
        return False
    data = res.get("data", {})
    if not data:
        return False
    items = data.get("items", [])
    if not items:
        return False
    return True


def _x_in_data(res, x):
    if not res:
        return None
    data = res.get("data", {})
    if not data:
        return None
    items = data.get("items", [])
    if not items:
        return None
    item = items[0]
    if not item:
        return None
    return item.get(x, None)


def _id_in_data(res):
    return _x_in_data(res, "id")


def _get_auth_session(auth_config: dict):
    global timeseries_client_auth_session
    if not timeseries_client_auth_session:
        # logger.info("CREATING SESSION:")
        timeseries_client_auth_session = create_auth_session(auth_config)
    return timeseries_client_auth_session


def _parse_request_json(res) -> typing.Tuple[typing.Dict, typing.Optional[str]]:
    try:
        res.raise_for_status()
        ret = res.json()
        ret["latigo-ok"] = True
        ret["latigo-error"] = None
        return ret, None
    except HTTPError as http_err:
        msg = f"Could not {res.request.method} @ {res.request.url}:\nHTTP error occurred: {http_err}"
        logger.error(msg)
        return {"latigo-ok": False, "latigo-error": msg}, msg
    except Exception as err:
        msg = f"Could not {res.request.method} @ {res.request.url}:\nOther error occurred: {err}"
        logger.error(msg)
        raise err
        return {"latigo-ok": False, "latigo-error": msg}, msg


class IMSMetadataAPIClient:
    def _parse_base_url(self):
        if "ims_meta_base_url" in self.config:
            self.base_url = self.config.pop("ims_meta_base_url")

    def _parse_auth_config(self):
        self.auth_config = self.config.get("ims_meta_auth", dict())
        self.session = _get_auth_session(self.auth_config)

    def __init__(self, config: dict):
        self.config = config
        if not self.config:
            raise Exception("No config specified")
        self._parse_auth_config()
        self._parse_base_url()

    def get_system_code_by_tag_name(self, tag_name: str) -> str:
        url = f"{self.base_url}/search/{urllib.parse.quote(tag_name)}"
        logger.info(url)
        res = self.session.get(url)
        obj, err = _parse_request_json(res)
        logger.info(pprint.pformat(obj))
        items = obj.get("data", {}).get("items", [])
        return items[0].get("systemCode", None) if len(items) > 0 else None


"""
    1028548d-6e15-4cef-bab3-467d1b37f700-28 ser ut som en av våre
    Choke -monitorering på Grane
        """


class IMSSubscriptionAPIClient:
    def _parse_base_url(self):
        self.base_url = self.config.get("ims_subscription_base_url", None)

    def _parse_auth_config(self):
        self.auth_config = self.config.get("ims_subscription_auth", dict())
        self.session = _get_auth_session(self.auth_config)

    def __init__(self, config: dict):
        self.config = config
        if not self.config:
            raise Exception("No config specified")
        self._parse_auth_config()
        self._parse_base_url()

    def get_time_series_id_for_system_code(self, tag_name: str, system_code: str):
        url = f"{self.base_url}/uid/{urllib.parse.quote(system_code)}"
        logger.info(url)
        res = self.session.get(url)
        obj, err = _parse_request_json(res)
        logger.info(pprint.pformat(obj))
        items = obj.get("data", {}).get("items", [])
        return items[0].get("timeseriesId", None) if len(items) > 0 else None


class TimeSeriesAPIClient:
    def _parse_base_url(self):
        if "base_url" in self.config:
            self.base_url = self.config.pop("base_url")

    def _parse_auth_config(self):
        self.auth_config = self.config.get("auth", dict())
        self.session = _get_auth_session(self.auth_config)

    def _prepare_ims_meta_client(self):
        self.ims_meta = IMSMetadataAPIClient(self.conf)

    def _prepare_ims_subscription_client(self):
        self.ims_subscription = IMSSubscriptionAPIClient(self.conf)

    def __init__(self, config: dict):
        self.config = config
        if not self.config:
            raise Exception("No config specified")
        self._parse_auth_config()
        self._parse_base_url()
        self.do_async = self.config.get("async", False)
        # self._prepare_ims_meta_client();
        # self._prepare_ims_subscription_client();

    def get_timeseries_id_for_tag_name(self, tag_name: str):
        system_code = self.ims_meta.get_system_code_by_tag_name(tag_name=tag_name)
        if not system_code:
            return None
        return self.ims_subscription.get_time_series_id_for_system_code(system_code=system_code)

    def get_timeseries_id_for_tag_name_cached(self, tag_name: str):
        # TODO: Implement cache
        return self.get_timeseries_id_for_tag_name(tag_name=tag_name)

    def _fetch_data(self, id: str, time_range: TimeRange) -> typing.Tuple[typing.Dict, typing.Optional[str]]:
        url = f"{self.base_url}/{id}/data"
        params = {"startTime": time_range.rfc3339_from(), "endTime": time_range.rfc3339_to(), "limit": 100000, "includeOutsidePoints": True}
        res = self.session.get(url, params=params)
        return _parse_request_json(res)

    def _get_id_by_name(self, name: str, asset_id: typing.Optional[str] = None) -> typing.Dict:
        body = {"name": name}
        if asset_id:
            body["assetId"] = asset_id
        # logger.info("Getting:")        logger.info(pprint.pformat(body))
        res = self.session.get(self.base_url, params=body)
        obj, err = _parse_request_json(res)
        # logger.info(pprint.pformat(obj))
        return obj

    def _id_exists_for_name(self, name: str, asset_id: typing.Optional[str] = None) -> bool:
        res = self._get_id_by_name(name=name, asset_id=asset_id)
        return _itemes_present(res)

    def _create_id(self, name: str, description: str = "", unit: str = "", asset_id: str = "", external_id: str = ""):
        body = {"name": name, "description": description, "step": True, "unit": unit, "assetId": asset_id, "externalId": external_id}
        logger.info("Posting:")
        logger.info(pprint.pformat(body))
        res = self.session.post(self.base_url, json=body, params=None)
        obj, err = _parse_request_json(res)
        logger.info(pprint.pformat(obj))
        return obj

    def _create_id_if_not_exists(self, name: str, description: str = "", unit: str = "", asset_id: str = "", external_id: str = ""):
        meta = self._get_id_by_name(name=name, asset_id=asset_id)
        if not _itemes_present(meta):
            return self._create_id(name, description, unit, asset_id, external_id)
        return meta

    def _store_data_for_id(self, id: str, data: typing.Iterable[typing.Tuple[str, pd.DataFrame, typing.List[str]]]):
        datapoints = []
        datapoints.append({"time": "2019-04-12T08:13:44.154Z", "value": 0.5, "status": 2147483843})
        body = {"datapoints": datapoints}
        url = f"{self.base_url}/{id}/data"
        res = self.session.post(url, json=body, params=None)
        return _parse_request_json(res)

    def _store_data_by_id(self, id: str, data: dict):
        url = f"{self.base_url}/timeseries/v1.5/{id}/data?async={self.do_async}"
        res = self.session.post(url, data=data)
        return _parse_request_json(res)


def _get_items(datas: dict) -> typing.List:
    if not datas:
        logger.info("NO DATAS")
        return []
    data = datas.get("data", {})
    if not data:
        logger.info("NO DATA")
        return []
    return data.get("items", [])


class TimeSeriesAPISensorDataProvider(TimeSeriesAPIClient, SensorDataProviderInterface):
    def __init__(self, config: dict):
        super().__init__(config)
        self._parse_auth_config()
        self._parse_base_url()

    def get_data_for_range(self, spec: SensorDataSpec, time_range: TimeRange) -> typing.Tuple[typing.Optional[SensorData], typing.Optional[str]]:
        """
        return the actual data as per the range specified
        """
        missing_meta = 0
        missing_id = 0
        completed = 0
        data: typing.List[dict] = []
        if len(spec.tag_list) < 0:
            logger.warning("Tag list empty")
        for tag in spec.tag_list:
            logger.info(f"GETTING DATA FOR {tag}")
            meta = self._get_id_by_name(name=tag.name, asset_id=tag.asset)
            if not meta:
                missing_meta += 1
                continue
            id = _id_in_data(meta)
            if not id:
                missing_id += 1
                continue
            ts, err = self._fetch_data(id, time_range)
            if err or not ts.get("latigo-ok", False):
                return None, ts.get("latigo-error", "Unknon failure")
            data += _get_items(ts)
            completed += 1
        data = transform_from_timeseries_to_gordo(data)
        return SensorData(time_range=time_range, data=data), None


class TimeSeriesAPIPredictionStorageProvider(TimeSeriesAPIClient, PredictionStorageProviderInterface):
    def __init__(self, config: dict):
        super().__init__(config)

    def put_predictions(self, prediction_data: PredictionData):
        """
        Store prediction data in time series api
        """
        name = "test"
        description = "test for latigo"
        unit = "Kg"
        asset_id = "test_asset_id"
        external_id = "test_external_id"
        data = prediction_data.data
        meta = self._create_id_if_not_exists(name=name, description=description, unit=unit, asset_id=asset_id, external_id=external_id)
        logger.info(f"GOT META: {meta}")
        id = _id_in_data(meta)
        if not id:
            raise Exception(f"No ID returned from Time Series API for {name}")
        obj, err = self._store_data_for_id(id=id, data=data)
        # logger.info(pprint.pformat(obj))
        return obj
