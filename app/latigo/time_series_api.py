import typing
import logging
import math
import requests
import datetime
import json
import pprint
from requests.exceptions import HTTPError
import pandas as pd
import urllib.parse

from latigo.types import Task, SensorDataSpec, SensorDataSet, TimeRange, PredictionDataSet, LatigoSensorTag
from latigo.intermediate import IntermediateFormat
from latigo.sensor_data import SensorDataProviderInterface
from latigo.prediction_storage import PredictionStorageProviderInterface
from latigo.utils import rfc3339_from_datetime
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
    logger.info(f"tagnames: {tag_names} tagmap {tag_names_map} tagdata {tag_names_data}")
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
    if not isinstance(res, dict):
        return None
    data = res.get("data", {})
    if not isinstance(data, dict):
        return None
    items = data.get("items", [])
    if not isinstance(items, list):
        return None
    if len(items) < 1:
        return None
    item = items[0]
    if not isinstance(item, dict):
        return None
    return item.get(x, None)


def _find_tag_in_data(res, tag):
    if not isinstance(res, dict):
        return None
    data = res.get("data", {})
    if not isinstance(data, dict):
        return None
    items = data.get("items", [])
    if not isinstance(items, list):
        return None
    if len(items) < 1:
        return None
    for item in items:
        if not isinstance(item, dict):
            continue

        name = item.get("name", None)
        if not name:
            continue
        if tag == name:
            return item
    return None


def _id_in_data(res):
    return _x_in_data(res, "id")


def _get_items(datas: dict) -> typing.List:
    if not datas:
        logger.info("NO DATAS")
        return []
    data = datas.get("data", {})
    if not data:
        logger.info("NO DATA")
        return []
    return data.get("items", [])


def _get_auth_session(auth_config: dict, force: bool = False):
    global timeseries_client_auth_session
    if not timeseries_client_auth_session or force:
        # logger.info("CREATING SESSION:")
        timeseries_client_auth_session = create_auth_session(auth_config)
    return timeseries_client_auth_session


def _parse_request_json(res) -> typing.Tuple[typing.Optional[typing.Dict], typing.Optional[str]]:
    try:
        res.raise_for_status()
        ret = res.json()
        ret["latigo-ok"] = True
        ret["latigo-error"] = None
        return ret, None
    except HTTPError as http_err:
        msg = f"Could not {res.request.method} @ {res.request.url}:\nHTTP error occurred: {http_err}. Body was '{res.request.body}'"
        logger.error(msg)
        return None, msg
    except Exception as err:
        msg = f"Could not {res.request.method} @ {res.request.url}:\nOther error occurred: {err}"
        logger.error(msg)
        # raise err
        return None, msg
    return None, "ERRROR"


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

    def get_system_code_by_tag_name(self, tag_name: str) -> typing.Optional[str]:
        url = f"{self.base_url}/search/{urllib.parse.quote(tag_name)}"
        logger.info(url)
        res = self.session.get(url)
        obj, err = _parse_request_json(res)
        if obj:
            logger.info(pprint.pformat(obj))
            items = obj.get("data", {}).get("items", [])
            return items[0].get("systemCode", None) if len(items) > 0 else None
        else:
            logger.warning(f"Could not get system code by tag name: {err}")
        return None


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
        if obj:
            logger.info(pprint.pformat(obj))
            items = obj.get("data", {}).get("items", [])
            return items[0].get("timeseriesId", None) if len(items) > 0 else None
        else:
            logger.warning(f"Could not get time series id by system code: {err}")
        return None


class TimeSeriesAPIClient:
    def __str__(self):
        return f"TimeSeriesAPIClient({self.base_url})"

    def _fail(self, message):
        self.good_to_go = False
        logger.error(message)
        logger.warning("Using config:")
        logger.warning(self.config)
        return None

    def _parse_base_url(self):
        self.base_url = self.config.get("base_url", None)
        if not self.base_url:
            return self._fail("No base_url found in config")
        # logger.info(f"Using base_url: '{self.base_url}'")

    def _create_session(self, force: bool = False):
        self.session = _get_auth_session(self.auth_config, force)
        if not self.session:
            return self._fail(f"Could not create session with force={force}")

    def _parse_auth_config(self):
        self.auth_config = self.config.get("auth", dict())
        if not self.auth_config:
            return self._fail("No auth_config found in config")
        self._create_session(force=False)

    def _prepare_ims_meta_client(self):
        self.ims_meta = IMSMetadataAPIClient(self.conf)
        if not self.ims_meta:
            return self._fail("Could not create ims_meta")

    def _prepare_ims_subscription_client(self):
        self.ims_subscription = IMSSubscriptionAPIClient(self.conf)
        if not self.ims_subscription:
            return self._fail("Could not create ims_subscription")

    def __init__(self, config: dict):
        self.good_to_go = True
        self.config = config
        if not self.config:
            raise Exception("No config specified")
        self._parse_auth_config()
        self._parse_base_url()
        self.do_async = self.config.get("async", False)
        # self._prepare_ims_meta_client();
        # self._prepare_ims_subscription_client();
        if not self.good_to_go:
            raise Exception("TimeSeriesAPIClient failed. Please see previous errors for clues as to why")

    def get_timeseries_id_for_tag_name(self, tag_name: str):
        system_code = self.ims_meta.get_system_code_by_tag_name(tag_name=tag_name)
        if not system_code:
            return None
        return self.ims_subscription.get_time_series_id_for_system_code(system_code=system_code)

    def get_timeseries_id_for_tag_name_cached(self, tag_name: str):
        # TODO: Implement cache
        return self.get_timeseries_id_for_tag_name(tag_name=tag_name)

    def _get(self, *args, **kwargs):
        res = None
        try:
            res = self.session.get(*args, **kwargs)
        except oauthlib.oauth2.rfc6749.errors.MissingTokenError:
            logger.info("Token expired, retrying GET after recreating session")
            self._create_session(force=True)
            res = self.session.get(*args, **kwargs)
        return res

    def _post(self, *args, **kwargs):
        res = None
        try:
            res = self.session.post(*args, **kwargs)
        except oauthlib.oauth2.rfc6749.errors.MissingTokenError:
            logger.info("Token expired, retrying POST after recreating session")
            self._create_session(force=True)
            res = self.session.post(*args, **kwargs)
        return res

    def _fetch_data_for_id(self, id: str, time_range: TimeRange) -> typing.Tuple[typing.Optional[typing.Dict], typing.Optional[str]]:
        url = f"{self.base_url}/{id}/data"
        params = {"startTime": time_range.rfc3339_from(), "endTime": time_range.rfc3339_to(), "limit": 100000, "includeOutsidePoints": True}
        res = self._get(url=url, params=params)
        return _parse_request_json(res)

    def _get_meta_by_name(self, name: str, asset_id: typing.Optional[str] = None) -> typing.Tuple[typing.Optional[typing.Dict], typing.Optional[str]]:
        body = {"name": name}
        if name is None:
            return None, "No name specified"
            # raise Exception("NO NAME")
        if asset_id:
            # NOTE: This is disaabled on purpose because gordo provide asset ids that are sometimes incompatible with time series api
            # logger.warning("Excluding asset-id from metadata call in time series api because gordo provide asset ids that are sometimes incompatible with time series api")
            # body["assetId"] = asset_id
            pass
        # logger.info(f"Getting {pprint.pformat(body)} from {self.base_url}")
        res = self._get(self.base_url, params=body)
        return _parse_request_json(res)

    def _create_id(self, name: str, description: str = "", unit: str = "", asset_id: str = "", external_id: str = ""):
        body = {"name": name, "description": description, "step": True, "unit": unit, "assetId": asset_id, "externalId": external_id}
        # logger.info(f"Posting {pprint.pformat(body)} from {self.base_url}")
        res = self._post(self.base_url, json=body, params=None)
        return _parse_request_json(res)

    def _create_id_if_not_exists(self, name: str, description: str = "", unit: str = "", asset_id: str = "", external_id: str = ""):
        meta, err = self._get_meta_by_name(name=name, asset_id=asset_id)
        if meta and _itemes_present(meta):
            return meta, err
        return self._create_id(name, description, unit, asset_id, external_id)

    def _store_data_for_id(self, id: str, datapoints: typing.List[typing.Dict[str, str]]):
        body = {"datapoints": datapoints}
        url = f"{self.base_url}/{id}/data"
        res = self._post(url, json=body, params=None)
        return _parse_request_json(res)


def row_count(data):
    return len(data)


class TimeSeriesAPISensorDataProvider(TimeSeriesAPIClient, SensorDataProviderInterface):
    def __init__(self, config: dict):
        super().__init__(config)
        self._parse_auth_config()
        self._parse_base_url()

    def __str__(self):
        return f"TimeSeriesAPISensorDataProvider({self.base_url})"

    def supports_tag(self, tag: LatigoSensorTag) -> bool:
        meta, err = self._get_meta_by_name(name=tag.name, asset_id=tag.asset)
        if meta and _itemes_present(meta):
            return True
        return False

    def get_data_for_range(self, spec: SensorDataSpec, time_range: TimeRange) -> typing.Tuple[typing.Optional[SensorDataSet], typing.Optional[str]]:
        """
        return the actual data as per the range specified
        """
        fail_on_missing = True
        missing_meta = 0
        missing_id = 0
        completed = 0
        data: typing.List[typing.Dict] = []
        if len(spec.tag_list) <= 0:
            logger.warning("Tag list empty")
        for tag in spec.tag_list:
            if not tag:
                return None, f"Invalid tag"
            tag_type = type(tag)
            if not isinstance(tag, LatigoSensorTag):
                return None, f"Invalid tag type '{tag_type}'"
            name = tag.name
            if not name:
                return None, f"Invalid tag name={name}"
            # asset_id = tag_dict.get("asset")
            asset_id = tag.asset
            if not asset_id:
                return None, f"Invalid tag asset_id={asset_id}"
            meta, err = self._get_meta_by_name(name=name, asset_id=asset_id)
            # logger.info(f" O '{meta}, {err}'")
            if not meta:
                missing_meta += 1
                if fail_on_missing:
                    break
                continue
            item = _find_tag_in_data(meta, name)
            id = None
            if item:
                id = item.get("id", None)
            if not id:
                missing_id += 1
                logger.warning(f"Time series not found for requested tag '{tag}', skipping")
                # logger.warning(pprint.pformat(meta))
                if fail_on_missing:
                    break
                continue
            ts, err = self._fetch_data_for_id(id, time_range)
            # logger.info(f" D '{ts}, {err}'")
            if err or not ts:
                if ts:
                    msg = ts.get("latigo-ok", "Unknown failure")
                else:
                    msg = "No ts"
                return None, err or msg
            data.extend(_get_items(ts))
            completed += 1
        if missing_meta > 0:
            logger.warning(f"Meta missing for {missing_meta} tags")
            if fail_on_missing:
                return None, f"Meta missing for {missing_meta} tags"
        if missing_id > 0:
            logger.warning(f"ID missing for {missing_id} tags")
            if fail_on_missing:
                return None, f"ID missing for {missing_id} tags"
        if not data:
            logger.warning("No gordo data")
        info = IntermediateFormat()
        if completed == len(spec.tag_list):
            info.from_time_series_api(data)
            rows = len(info)
            if rows > 0:
                logger.info(f"Completed fetching {rows} rows from {completed} tags")
            else:
                return None, f"No rows found in {completed} tags"
        else:
            return None, f"Not all tags fetched ({completed}/{len(spec.tag_list)})"
        return SensorDataSet(time_range=time_range, data=info), None


invalid_operations = ["start", "end", "model-input"]


def prediction_data_naming_convention(operation: str, model_name: str, tag_name: str, separator: str = "|", global_tag_name: str = "INDICATOR", global_model_name: str = "UNKNOWN_MODEL"):
    if operation in invalid_operations:
        return None
    if not tag_name:
        tag_name = global_tag_name
    if not model_name:
        model_name = global_model_name
    # Escape separator
    replacement = "_" if separator == "-" else "-"
    tag_name = tag_name.replace(separator, replacement)
    model_name = model_name.replace(separator, replacement)
    operation = operation.replace(separator, replacement)
    return f"{tag_name}{separator}{model_name}{separator}{operation}"


class TimeSeriesAPIPredictionStorageProvider(TimeSeriesAPIClient, PredictionStorageProviderInterface):
    def __init__(self, config: dict):
        super().__init__(config)

    def __str__(self):
        return f"TimeSeriesAPIPredictionStorageProvider({self.base_url})"

    def put_predictions(self, prediction_data: PredictionDataSet):
        """
        Store prediction data in time series api
        """
        # logger.info("Got predictions:")
        # logger.info(pprint.pformat(prediction_data))
        # logger.info("")
        data = prediction_data.data
        if not data:
            logger.warning("No prediction data for storing")
            return None
        output_tag_names: typing.Dict[typing.Tuple[str, str], str] = {}
        output_time_series_ids: typing.Dict[typing.Tuple[str, str], str] = {}
        row = data[0]
        # logger.info("ROW:")
        # logger.info(row)
        df = row[1]
        model_name = prediction_data.meta_data.get("model_name", "")
        for col in df.columns:
            output_tag_name = prediction_data_naming_convention(operation=col[0], model_name=model_name, tag_name=col[1])
            if not output_tag_name:
                # logger. info("Skipping invalid output tag name: {output_tag_name}")
                continue
            output_time_series_ids[col] = ""
            description = f"Gordo prediction for {col[0]} - {col[1]}"
            # Units cannot be derrived easily. Should be provided by prediction execution provider or set to none
            unit = ""
            # TODO: Should we generate some external_id?
            external_id = ""
            meta, err = self._create_id_if_not_exists(name=output_tag_name, description=description, unit=unit, external_id=external_id)
            if not meta and not err:
                err = "Meta mising with no error"
            if err:
                logger.error(f"Could not create/find id for name {output_tag_name}: {err}")
                continue
            id = _id_in_data(meta)
            if not id:
                logger.error(f"Could not get ID for {output_tag_name}")
                continue
            output_tag_names[col] = output_tag_name
            output_time_series_ids[col] = id
        failed_tags = 0
        stored_tags = 0
        skipped_values = 0
        stored_values = 0
        logger.info(f"Storing {len(df.columns)} predictions:")
        for key, item in df.items():
            operation, tag_name = key
            if operation in invalid_operations:
                continue
            datapoints = []
            id = output_time_series_ids[key]
            # logger.info(f"Key({key}) id={id}")
            for time, value in item.items():
                stored_values += 1
                # logger.info(f"  Item({time}, {value})")
                if math.isnan(value):
                    # logger.info(f"Skipping NaN value for {key} @ {time}")
                    skipped_values += 1
                    continue
                datapoints.append({"time": rfc3339_from_datetime(time), "value": value, "status": "0"})
            res, err = self._store_data_for_id(id=id, datapoints=datapoints)
            if not res or err:
                logger.error(f" Could not store data: {err}")
                failed_tags += 1
            else:
                stored_tags += 1
        logger.info(f"  {stored_values} values stored, {skipped_values} NaNs skipped. {stored_tags} tags stored, {failed_tags} tags failed")
        # with pd.option_context("display.max_rows", None, "display.max_columns", None):
        #    logger.info("")
        #    logger.info(f"  Item({item})")

        return None
