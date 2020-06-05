import json
from unittest.mock import patch

from requests import Response

from tests.factories.metadata_api import TimeSeriesIdMetadataFactory


def make_response(
    content: dict = None, dumped_data: str = None, status_code: int = 200, reason: str = "OK"
) -> Response:
    response_obj = Response()
    response_obj.status_code = status_code
    response_obj._content = dumped_data if dumped_data else _dump_any_dict(content).encode()
    response_obj.reason = reason
    return response_obj


def _dump_any_dict(target: dict) -> str:
    return json.dumps(target, sort_keys=True, default=str)


def test_get_projects(metadata_api_client):
    projects = ["ioc-1000", "ioc-1099"]
    with patch.object(metadata_api_client, "get", return_value=make_response(content={"projects": projects})):
        res = metadata_api_client.get_projects()
    assert res == projects


def test_send_time_series_id_metadata(metadata_api_client):
    ts_id_metadata = TimeSeriesIdMetadataFactory()
    expected = ts_id_metadata.__dict__
    expected["model_id"] = 1226976
    expected = _dump_any_dict(expected)

    with patch.object(metadata_api_client, "post", return_value=make_response(dumped_data=expected)):
        res = metadata_api_client.send_time_series_id_metadata(ts_id_metadata)
    assert res.content == expected
