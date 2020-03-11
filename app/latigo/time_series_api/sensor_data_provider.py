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
from oauthlib.oauth2.rfc6749.errors import MissingTokenError

from latigo.types import (
    Task,
    SensorDataSpec,
    SensorDataSet,
    TimeRange,
    PredictionDataSet,
    LatigoSensorTag,
)
from latigo.intermediate import IntermediateFormat
from latigo.sensor_data import SensorDataProviderInterface
from latigo.prediction_storage import PredictionStorageProviderInterface
from latigo.utils import rfc3339_from_datetime
import requests_ms_auth

from .misc import _itemes_present
from .client import TimeSeriesAPIClient

logger = logging.getLogger(__name__)


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

    def __str__(self):
        return f"TimeSeriesAPISensorDataProvider({self.base_url})"

    def supports_tag(self, tag: LatigoSensorTag) -> bool:
        meta, err = self._get_meta_by_name(name=tag.name, asset_id=tag.asset)
        if meta and _itemes_present(meta):
            return True
        return False

    def get_data_for_range(
        self, spec: SensorDataSpec, time_range: TimeRange
    ) -> typing.Tuple[typing.Optional[SensorDataSet], typing.Optional[str]]:
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
                logger.warning(
                    f"Time series not found for requested tag '{tag}', skipping"
                )
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
