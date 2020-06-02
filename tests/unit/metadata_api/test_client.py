import json
from unittest.mock import patch

from requests import Response

get_projects_resp = {
    "projects": [
        "ioc-1000",
        "ioc-1099",
    ]
}


def make_response(content: dict, status_code: int = 200, reason: str = "OK") -> Response:
    response_obj = Response()
    response_obj.status_code = status_code
    response_obj._content = json.dumps(content).encode()
    response_obj.reason = reason
    return response_obj


def test_get_projects(metadata_api_client):
    with patch.object(metadata_api_client, "get", return_value=make_response(content=get_projects_resp)):
        res = metadata_api_client.get_projects()
    assert res == ["ioc-1000", "ioc-1099"]
