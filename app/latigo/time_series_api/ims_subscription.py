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

from .misc import _get_auth_session, _parse_request_json
from .cache import *

logger = logging.getLogger(__name__)


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
