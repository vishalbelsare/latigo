import logging
from datetime import datetime
from time import sleep
from unittest.mock import ANY, call, patch

from latigo.time_series_api.misc import _itemes_present
from latigo.types import TimeRange
from tests.conftest import make_response

logger = logging.getLogger(__name__)


tsapi_data = {
    "data": {
        "items": [
            {
                "id": "c530a095-b86e-4adb-9fae-78b9e3974f48",
                "name": "tag_1",
                "unit": "some_unit_1",
                "datapoints": [
                    {"time": "2019-06-10T21:00:07.616Z", "value": 69.69, "status": 420},
                    {"time": "2019-06-10T21:10:07.616Z", "value": 42.69, "status": 420},
                    {
                        "time": "2019-06-10T21:20:07.616Z",
                        "value": 1337.69,
                        "status": 1337,
                    },
                    {
                        "time": "2019-06-10T21:30:07.616Z",
                        "value": 1337.69,
                        "status": 1337,
                    },
                ],
            }
        ]
    }
}

tsapi_datas = [
    {
        "id": "c530a095-b86e-4adb-9fae-78b9e3974f48",
        "name": "tag_1",
        "unit": "some_unit_1",
        "datapoints": [
            {"time": "2019-06-10T21:00:07.616Z", "value": 69.69, "status": 420},
            {"time": "2019-06-10T21:10:07.616Z", "value": 42.69, "status": 420},
            {"time": "2019-06-10T21:20:07.616Z", "value": 1337.69, "status": 1337},
            {"time": "2019-06-10T21:30:07.616Z", "value": 1337.69, "status": 1337},
        ],
    },
    {
        "id": "9f9c003c-ab5d-4a25-830c-60fb5499805f",
        "name": "tag_2",
        "unit": "some_unit_2",
        "datapoints": [
            {"time": "2019-06-10T21:00:07.616Z", "value": 42, "status": 69},
            {"time": "2019-06-10T21:10:07.616Z", "value": 420, "status": 69},
            {"time": "2019-06-10T21:20:07.616Z", "value": 420, "status": 69},
        ],
    },
]


def test_itemes_present():
    assert False == _itemes_present(None)
    assert False == _itemes_present({})
    assert False == _itemes_present({"data": {}})
    assert False == _itemes_present({"data": {"items": []}})
    assert True == _itemes_present({"data": {"items": ["something"]}})


def test_get_meta_by_name(time_series_api_client):
    tag_name = "1901.A-21T.MA_Y"
    asset_id = "1901"
    tag_metadata = {"data": []}

    assert time_series_api_client._tag_metadata_cache.get_metadata(tag_name, asset_id) is None

    with patch.object(time_series_api_client, "_get_metadata_from_api", return_value=tag_metadata):
        res = time_series_api_client.get_meta_by_name(tag_name, asset_id)

    assert res == tag_metadata
    assert time_series_api_client._tag_metadata_cache.get_metadata(tag_name, asset_id) == tag_metadata


def test_value_in_cache_is_expired(time_series_api_client):
    tag_name = "1901.A-21T.MA_Y"
    asset_id = "1901"
    tag_metadata = {"data": []}
    seconds_to_expire = 1
    cache = time_series_api_client._tag_metadata_cache
    cache.CACHE_TIME_TO_LIVE = seconds_to_expire

    cache.set_metadata(tag_name, asset_id, tag_metadata)
    assert cache.get_metadata(tag_name, asset_id) == tag_metadata

    sleep(seconds_to_expire)
    assert cache.get_metadata(tag_name, asset_id) is None


def test_fetch_data_for_multiple_ids(time_series_api_client):
    datetime_from = datetime.fromisoformat("2020-04-10T10:00:00.000000+00:00")
    datetime_to = datetime.fromisoformat("2020-04-10T10:30:00.000000+00:00")
    time_range = TimeRange(from_time=datetime_from, to_time=datetime_to)
    tag_ids = [str(i) for i in range(1, 110)]

    response_data = [make_response({"data": {"items": []}}) for _ in tag_ids]
    expected_calls = [
        call(url=ANY, json=[_make_multiple_ids_req_data(tag_id, time_range) for tag_id in tag_ids[:100]]),
        call(url=ANY, json=[_make_multiple_ids_req_data(tag_id, time_range) for tag_id in tag_ids[100:]]),
    ]
    with patch.object(time_series_api_client, "_post", side_effect=response_data) as mocked_post:
        time_series_api_client._fetch_data_for_multiple_ids(tag_ids=tag_ids, time_range=time_range)

    mocked_post.assert_has_calls(expected_calls)


def _make_multiple_ids_req_data(tag_id: str, time_range: TimeRange):
    return {
        "id": tag_id,
        "startTime": time_range.rfc3339_from(),
        "endTime": time_range.rfc3339_to(),
        "limit": 100000,
        "includeOutsidePoints": False,
    }
