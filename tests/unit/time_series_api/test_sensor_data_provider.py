from datetime import datetime
from unittest.mock import patch

from latigo.types import TimeRange
from tests.factories.time_series_api import SensorDataSpecFactory

from tests.unit.time_series_api.conftest import (
    get_meta_by_name_resp,
    fetch_data_for_multiple_ids_resp,
    make_sensor_data_set,
)


def test_get_data_for_range(ts_api):
    datetime_from = datetime.fromisoformat("2020-04-10T10:00:00.000000+00:00")
    datetime_to = datetime.fromisoformat("2020-04-10T10:30:00.000000+00:00")
    time_range = TimeRange(from_time=datetime_from, to_time=datetime_to)
    spec = SensorDataSpecFactory()
    tags_data_from_api = fetch_data_for_multiple_ids_resp([str(i) for i in range(len(spec.tag_list))])

    with patch.object(
        ts_api,
        "get_meta_by_name",
        side_effect=[get_meta_by_name_resp(tag_id=str(i), name=tag.name) for i, tag in enumerate(spec.tag_list)],
    ), patch.object(ts_api, "_fetch_data_for_multiple_ids", return_value=tags_data_from_api):
        res = ts_api.get_data_for_range(spec=spec, time_range=time_range)

    expected = make_sensor_data_set(from_time=datetime_from, to_time=datetime_to, tags_data=tags_data_from_api), None
    assert res == expected
