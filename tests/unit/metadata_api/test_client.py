from unittest.mock import patch

from tests.conftest import dump_any_dict, make_response
from tests.factories.metadata_api import TimeSeriesIdMetadataFactory


def test_get_projects(metadata_api_client):
    projects = ["ioc-1000", "ioc-1099"]
    with patch.object(metadata_api_client, "get", return_value=make_response(content={"projects": projects})):
        res = metadata_api_client.get_projects()
    assert res == projects


def test_send_time_series_id_metadata(metadata_api_client):
    ts_id_metadata = TimeSeriesIdMetadataFactory()
    expected = ts_id_metadata.__dict__
    expected["model_id"] = 1226976
    expected = dump_any_dict(expected)

    with patch.object(metadata_api_client, "post", return_value=make_response(dumped_data=expected)):
        res = metadata_api_client.send_time_series_id_metadata(ts_id_metadata)
    assert res.content == expected
