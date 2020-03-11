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

from .misc import _itemes_present, _get_auth_session, _parse_request_json
from .cache import *

logger = logging.getLogger(__name__)


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
        self.meta_data_cache = MetaDataCache()
        self._parse_auth_config()
        self._parse_base_url()
        self.do_async = self.config.get("async", False)
        # self._prepare_ims_meta_client();
        # self._prepare_ims_subscription_client();
        if not self.good_to_go:
            raise Exception(
                "TimeSeriesAPIClient failed. Please see previous errors for clues as to why"
            )

    #    def get_timeseries_id_for_tag_name(self, tag_name: str):
    #        system_code = self.ims_meta.get_system_code_by_tag_name(tag_name=tag_name)
    #        if not system_code:
    #            return None
    #        return self.ims_subscription.get_time_series_id_for_system_code(system_code=system_code)

    def _get(self, *args, **kwargs):
        res = None
        try:
            res = self.session.get(*args, **kwargs)
        except MissingTokenError:
            logger.info("Token expired, retrying GET after recreating session")
            self._create_session(force=True)
            res = self.session.get(*args, **kwargs)
        return res

    def _post(self, *args, **kwargs):
        res = None
        try:
            res = self.session.post(*args, **kwargs)
        except MissingTokenError:
            logger.info("Token expired, retrying POST after recreating session")
            self._create_session(force=True)
            res = self.session.post(*args, **kwargs)
        return res

    def _fetch_data_for_id(
        self, id: str, time_range: TimeRange
    ) -> typing.Tuple[typing.Optional[typing.Dict], typing.Optional[str]]:
        url = f"{self.base_url}/{id}/data"
        params = {
            "startTime": time_range.rfc3339_from(),
            "endTime": time_range.rfc3339_to(),
            "limit": 100000,
            "includeOutsidePoints": True,
        }
        res = self._get(url=url, params=params)
        return _parse_request_json(res)

    def _get_meta_by_name_raw(
        self, name: str, asset_id: typing.Optional[str] = None
    ) -> typing.Tuple[typing.Optional[typing.Dict], typing.Optional[str]]:
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

    def _get_meta_by_name(
        self, name: str, asset_id: typing.Optional[str] = None
    ) -> typing.Tuple[typing.Optional[typing.Dict], typing.Optional[str]]:
        if self.meta_data_cache:
            meta = self.meta_data_cache.get_meta(name, asset_id)
            if meta:
                return meta, None
        meta, msg = self._get_meta_by_name_raw(name, asset_id)
        if meta:
            self.meta_data_cache.set_meta(name, asset_id, meta)
        return meta, msg

    def _create_id(
        self,
        name: str,
        description: str = "",
        unit: str = "",
        asset_id: str = "",
        external_id: str = "",
    ):
        body = {
            "name": name,
            "description": description,
            "step": True,
            "unit": unit,
            "assetId": asset_id,
            "externalId": external_id,
        }
        # logger.info(f"Posting {pprint.pformat(body)} from {self.base_url}")
        res = self._post(self.base_url, json=body, params=None)
        return _parse_request_json(res)

    def _create_id_if_not_exists(
        self,
        name: str,
        description: str = "",
        unit: str = "",
        asset_id: str = "",
        external_id: str = "",
    ):
        meta, err = self._get_meta_by_name(name=name, asset_id=asset_id)
        if meta and _itemes_present(meta):
            return meta, err
        return self._create_id(name, description, unit, asset_id, external_id)

    def _store_data_for_id(
        self, id: str, datapoints: typing.List[typing.Dict[str, str]]
    ):
        body = {"datapoints": datapoints}
        url = f"{self.base_url}/{id}/data"
        res = self._post(url, json=body, params=None)
        return _parse_request_json(res)
