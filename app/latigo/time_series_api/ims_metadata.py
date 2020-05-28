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

from .misc import get_auth_session, _parse_request_json
from .cache import *


logger = logging.getLogger(__name__)


class IMSMetadataAPIClient:
    def _parse_base_url(self):
        if "ims_meta_base_url" in self.config:
            self.base_url = self.config.pop("ims_meta_base_url")

    def _parse_auth_config(self):
        self.auth_config = self.config.get("ims_meta_auth", dict())
        self.session = get_auth_session(self.auth_config)

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
