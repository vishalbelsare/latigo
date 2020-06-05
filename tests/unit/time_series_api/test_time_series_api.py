import logging
from time import sleep
from unittest.mock import patch

from latigo.time_series_api.misc import _itemes_present

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
