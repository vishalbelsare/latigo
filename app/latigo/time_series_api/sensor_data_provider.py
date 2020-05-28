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
        meta, err = self.get_meta_by_name(name=tag.name, asset_id=tag.asset)
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
        # This is here to make typing explicit to help mypy to not fail
        # See https://github.com/equinor/latigo/pull/45
        tag_list: typing.List[LatigoSensorTag] = spec.tag_list
        if len(tag_list) <= 0:
            logger.warning("Tag list empty")
        for raw_tag in tag_list:
            if not raw_tag:
                return None, f"Invalid tag"
            tag_type = type(raw_tag)
            if not isinstance(raw_tag, LatigoSensorTag):
                return None, f"Invalid tag type '{tag_type}'"
            # This is here to make typing explicit to help mypy to not fail
            # See https://github.com/equinor/latigo/pull/45
            tag: LatigoSensorTag = raw_tag
            name = tag.name
            if not name:
                return None, f"Invalid tag name={name}"
            # asset_id = tag_dict.get("asset")
            asset_id = tag.asset
            if not asset_id:
                return None, f"Invalid tag asset_id={asset_id}"
            meta, err = self.get_meta_by_name(name=name, asset_id=asset_id)
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

        if completed == len(spec.tag_list):
            dataframes = SensorDataSet.to_gordo_dataframe(data, time_range.from_time, time_range.to_time)
        else:
            return None, f"Not all tags fetched ({completed}/{len(spec.tag_list)})"

        return SensorDataSet(time_range=time_range, data=dataframes), None
