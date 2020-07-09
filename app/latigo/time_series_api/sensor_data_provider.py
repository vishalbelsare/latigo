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
from ..log import measure

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


class TimeSeriesAPISensorDataProvider(TimeSeriesAPIClient, SensorDataProviderInterface):
    def __init__(self, config: dict):
        super().__init__(config)
        self._parse_auth_config()
        self._parse_base_url()

    def __str__(self):
        return f"TimeSeriesAPISensorDataProvider({self.base_url})"

    def supports_tag(self, tag: LatigoSensorTag) -> bool:
        meta = self.get_meta_by_name(name=tag.name, asset_id=tag.asset)
        if meta and _itemes_present(meta):
            return True
        return False

    @measure("get_data_for_range")
    def get_data_for_range(
        self, spec: SensorDataSpec, time_range: TimeRange
    ) -> typing.Tuple[typing.Optional[SensorDataSet], typing.Optional[str]]:
        """Fetch sensor data from TS API per the range.

        This func uses less calls to fetch the data: 1 call per 100 tags.
        """
        tag_list: typing.List[LatigoSensorTag] = spec.tag_list

        tag_ids_names: typing.Dict[str, str] = {}
        for raw_tag in tag_list:
            tag: LatigoSensorTag = raw_tag
            name = tag.name
            asset_id = tag.asset
            meta = self.get_meta_by_name(name=name, asset_id=asset_id)
            if not meta:
                raise ValueError("'meta' was not found for name '%s' and asset_id '%s'", name, asset_id)

            item = _find_tag_in_data(meta, name)
            tag_ids_names[item["id"]] = name

        tags_data = self._fetch_data_for_multiple_ids(tag_ids=tag_ids_names.keys(), time_range=time_range)
        empty_tags_ids = [tag_data["id"] for tag_data in tags_data if not tag_data.get("datapoints", None)]

        if empty_tags_ids:
            tags_data = [tag for tag in tags_data if tag["id"] not in empty_tags_ids]
            logger.warning("'datapoints' are empty for the following tags: %s", "; ".join(empty_tags_ids))

        if not tags_data:
            raise ValueError("No datapoints for tags where found.")

        for tag_data in tags_data:  # add "tag_name" to data cause TS API does not return it anymore
            tag_id = tag_data["id"]
            tag_data["name"] = tag_ids_names[tag_id]

        dataframes = SensorDataSet.to_gordo_dataframe(tags_data, time_range.from_time, time_range.to_time)
        return SensorDataSet(time_range=time_range, data=dataframes), None
