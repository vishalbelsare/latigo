import logging
from datetime import datetime
from time import sleep
from typing import Optional
from unittest.mock import ANY, call, patch

import pytest

from latigo.time_series_api.misc import _itemes_present
from latigo.types import TimeRange
from tests.conftest import make_response

logger = logging.getLogger(__name__)


def make_tag_object(ts_id: str = "001", facility: Optional[str] = "1755", name: str = "GRA-0001E.PV"):
    return {
        "id": ts_id,
        "name": name,
        "description": "pmp E",
        "step": False,
        "unit": "RPM",
        "assetId": "GRA",
        "facility": facility,
        "externalId": "GRA-15",
        "changedTime": "2020-03-26T03:09:00.000Z",
        "createdTime": "2020-03-26T03:09:00.000Z",
    }


def test_itemes_present():
    assert False == _itemes_present(None)
    assert False == _itemes_present({})
    assert False == _itemes_present({"data": {}})
    assert False == _itemes_present({"data": {"items": []}})
    assert True == _itemes_present({"data": {"items": ["something"]}})


def test_get_meta_by_name(time_series_api_client):
    tag_name = "1901.A-21T.MA_Y"
    facility = "1901"
    tag_metadata = {"data": []}

    assert time_series_api_client._tag_metadata_cache.get_metadata(tag_name, facility) is None

    with patch.object(time_series_api_client, "_get_metadata_from_api", return_value=tag_metadata):
        res = time_series_api_client.get_meta_by_name(tag_name, facility)

    assert res == tag_metadata
    assert time_series_api_client._tag_metadata_cache.get_metadata(tag_name, facility) == tag_metadata


def test_value_in_cache_is_expired(time_series_api_client):
    tag_name = "1901.A-21T.MA_Y"
    facility = "1901"
    tag_metadata = {"data": []}
    seconds_to_expire = 1
    cache = time_series_api_client._tag_metadata_cache
    cache.CACHE_TIME_TO_LIVE = seconds_to_expire

    cache.set_metadata(tag_name, facility, tag_metadata)
    assert cache.get_metadata(tag_name, facility) == tag_metadata

    sleep(seconds_to_expire)
    assert cache.get_metadata(tag_name, facility) is None


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


def test_fetch_tag_by_id(time_series_api_client):
    ts_id = "000001"
    expected_res = {"data": {"items": [make_tag_object(ts_id=ts_id)]}}
    with patch.object(time_series_api_client, "_get", return_value=make_response(expected_res)) as mocked_get:
        res = time_series_api_client.fetch_tag_by_id(ts_id)

    mocked_get.assert_called_once_with(url=f"{time_series_api_client.base_url}/{ts_id}")
    assert res == expected_res


def test_patch_tag_facility_by_id(time_series_api_client):
    ts_id = "000001"
    facility = "1900"
    expected_res = {"data": {"items": [make_tag_object(ts_id=ts_id, facility=facility)]}}
    with patch.object(time_series_api_client, "_patch", return_value=make_response(expected_res)) as mocked_patch:
        res = time_series_api_client.patch_tag_facility_by_id(ts_id=ts_id, facility=facility)

    mocked_patch.assert_called_once_with(url=f"{time_series_api_client.base_url}/{ts_id}", json={"facility": facility})
    assert res == expected_res


def test_get_facility_by_tag_name(time_series_api_client):
    tag_name = "name"
    facility = "1900"
    get_meta_by_name_resp = {"data": {"items": [make_tag_object(name=tag_name, facility=facility)]}}
    with patch.object(time_series_api_client, "get_meta_by_name", return_value=get_meta_by_name_resp):
        res = time_series_api_client.get_facility_by_tag_name(tag_name=tag_name)

    assert res == facility


def test_get_facility_by_tag_name_no_facility(time_series_api_client):
    tag_name = "name"
    get_meta_resp = {"data": {"items": [make_tag_object(name=tag_name, facility=None)]}}
    with patch.object(time_series_api_client, "get_meta_by_name", return_value=get_meta_resp):
        with pytest.raises(Exception) as e_info:
            time_series_api_client.get_facility_by_tag_name(tag_name=tag_name)

    error_message = f"tag 'facility' is empty for tag name '{tag_name}' with data: {get_meta_resp['data']['items'][0]}"
    assert str(e_info.value) == error_message


def test_get_only_item_from_metadata_success(time_series_api_client):
    tag_name = "tag_name"
    tag = make_tag_object(name=tag_name)
    metadata = {"data": {"items": [tag]}}

    res = time_series_api_client.get_only_item_from_metadata(metadata=metadata, tag_name=tag_name)
    assert res == tag


@pytest.mark.parametrize(
    "metadata, error_message",
    [
        ({"data": {"items": []}}, "No tag object were found in TS API for tag name"),
        (
            {"data": {"items": [make_tag_object(), make_tag_object()]}},
            "More then 1 tag object were found in TS API for tag name",
        ),
    ],
)
def test_get_only_item_from_metadata_error(metadata: dict, error_message, time_series_api_client):
    with pytest.raises(ValueError) as e_info:
        time_series_api_client.get_only_item_from_metadata(metadata=metadata, tag_name="tag_name")
    assert error_message in str(e_info.value)


def test_replace_cached_metadata_with_new(time_series_api_client):
    tag_name = "1901.A-21T.MA_Y"
    facility = "1901"
    tag_metadata = {"data": {"items": [make_tag_object()]}}

    assert time_series_api_client._tag_metadata_cache.get_metadata(tag_name, facility) is None

    with patch.object(
        time_series_api_client, "_get_metadata_from_api", return_value={"data": {"items": []}}
    ), patch.object(time_series_api_client, "_create_id", return_value=tag_metadata) as create_id_mocked:
        res = time_series_api_client.replace_cached_metadata_with_new(tag_name, facility, "description")

    assert res == tag_metadata
    create_id_mocked.assert_called_once_with(name=tag_name, facility=facility, description="description")
    assert time_series_api_client._tag_metadata_cache.get_metadata(tag_name, facility) == tag_metadata
