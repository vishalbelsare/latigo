import logging
import typing

import requests
import requests_ms_auth
from pandas import MultiIndex
from requests.exceptions import HTTPError

from latigo.types import PredictionDataSet

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
            requests_ms_auth.MsSessionConfig(**auth_config)
        )

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


MODEL_INPUT_OPERATION = "model-input"
INVALID_OPERATIONS = ["start", "end", MODEL_INPUT_OPERATION]
MISSING_TAG_NAME = "INDICATOR"


def prediction_data_naming_convention(
    operation: str,
    model_name: str,
    tag_name: str,
    common_asset_id: str,
    separator: str = "|",
    missing_tag_name: str = MISSING_TAG_NAME,
):
    if operation in INVALID_OPERATIONS:
        return None
    if not tag_name:
        tag_name = f"{common_asset_id}.{missing_tag_name}"
    if not model_name:
        raise Exception(f"'model_name' can not be empty")
    # Escape separator
    replacement = "_" if separator == "-" else "-"
    tag_name = tag_name.replace(separator, replacement)
    model_name = model_name.replace(separator, replacement)
    operation = operation.replace(separator, replacement)
    return f"{tag_name}{separator}{model_name}{separator}{operation}"


def make_prediction_metadata_description(prediction_data: PredictionDataSet) -> str:
    """Make description for prediction metadata."""
    return (
        f"Gordo prediction for project '{prediction_data.meta_data.project_name}', "
        f"model '{prediction_data.meta_data.model_name}'. "
        f"Prediction period: from '{prediction_data.time_range.from_time}' : to '{prediction_data.time_range.to_time}'"
    )


def make_output_tag_type(original_tag_name: str) -> str:
    """Make 'type' for output_tag metadata.

    Args:
        original_tag_name: original tag name that we got from the prediction results.
    """
    return "derived" if original_tag_name else "aggregated"


def make_output_tag_derived_from(tag_name: str) -> typing.Union[str, None]:
    """Make 'derived_from' for output_tag metadata."""
    return tag_name or None


def make_output_tag_description(operation: str, tag_name: str) -> str:
    """Make description for output_tag."""
    return f"Gordo {operation} - {tag_name}"


def get_common_asset_id(columns: MultiIndex) -> str:
    """Fetch common asset from tag name the dataframe columns where operation and tag name are.

    Return:
        '1903.R-29PST3037.MA_Y' -> '1903'. Split first non empty tag name with '.' and take first part as asset.
    """
    for operation, tag_name in columns:
        if tag_name:
            return tag_name.split(".")[0]
    raise Exception(
        f"Not common asset found in dataframe columns. Parsed data: " + "; ".join(col[1] for col in columns.values)
    )


def find_in_time_series_resp(res, x):
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


def get_time_series_id_from_response(res):
    """Get Time Series ID from the time series tag data."""
    return find_in_time_series_resp(res, "id")
