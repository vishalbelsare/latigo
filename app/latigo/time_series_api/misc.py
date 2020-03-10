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


def _get_auth_session(auth_config: dict, force: bool = False):
    global timeseries_client_auth_session
    if not timeseries_client_auth_session or force:
        timeseries_client_auth_session = requests_ms_auth.MsRequestsSession(
            auth_config=auth_config
        )
    return timeseries_client_auth_session


def _parse_request_json(
    res,
) -> typing.Tuple[typing.Optional[typing.Dict], typing.Optional[str]]:
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


invalid_operations = ["start", "end", "model-input"]


def prediction_data_naming_convention(
    operation: str,
    model_name: str,
    tag_name: str,
    separator: str = "|",
    global_tag_name: str = "INDICATOR",
    global_model_name: str = "UNKNOWN_MODEL",
):
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
