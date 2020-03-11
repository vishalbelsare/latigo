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


logger = logging.getLogger(__name__)


class MetaDataCache:
    def __init__(self):
        self._data = {}

    def _key(self, name: str, asset_id: typing.Optional[str]):
        return f"{name}-|#-{asset_id}"

    def get_meta(
        self, name: str, asset_id: typing.Optional[str]
    ) -> typing.Optional[typing.Dict]:
        key = self._key(name, asset_id)
        return self._data.get(key, None)

    def set_meta(
        self,
        name: str,
        asset_id: typing.Optional[str],
        meta: typing.Optional[typing.Dict],
    ):
        key = self._key(name, asset_id)
        if not meta:
            del self._data[key]
        else:
            self._data[key] = meta
