import logging
import pprint
import typing
from latigo.time_series_api import _x_in_data, _itemes_present, _id_in_data, _x_in_data, transform_from_timeseries_to_gordo, _get_items

logger = logging.getLogger(__name__)


tsapi_data = {"data": {"items": [{"id": "c530a095-b86e-4adb-9fae-78b9e3974f48", "name": "tag_1", "unit": "some_unit_1", "datapoints": [{"time": "2019-06-10T21:00:07.616Z", "value": 69.69, "status": 420}, {"time": "2019-06-10T21:10:07.616Z", "value": 42.69, "status": 420}, {"time": "2019-06-10T21:20:07.616Z", "value": 1337.69, "status": 1337}, {"time": "2019-06-10T21:30:07.616Z", "value": 1337.69, "status": 1337}]}]}}

tsapi_datas = [{"id": "c530a095-b86e-4adb-9fae-78b9e3974f48", "name": "tag_1", "unit": "some_unit_1", "datapoints": [{"time": "2019-06-10T21:00:07.616Z", "value": 69.69, "status": 420}, {"time": "2019-06-10T21:10:07.616Z", "value": 42.69, "status": 420}, {"time": "2019-06-10T21:20:07.616Z", "value": 1337.69, "status": 1337}, {"time": "2019-06-10T21:30:07.616Z", "value": 1337.69, "status": 1337}]}, {"id": "9f9c003c-ab5d-4a25-830c-60fb5499805f", "name": "tag_2", "unit": "some_unit_2", "datapoints": [{"time": "2019-06-10T21:00:07.616Z", "value": 42, "status": 69}, {"time": "2019-06-10T21:10:07.616Z", "value": 420, "status": 69}, {"time": "2019-06-10T21:20:07.616Z", "value": 420, "status": 69}]}]

# TODO: transform_from_timeseries_to_gordo

# TODO: transform_from_gordo_to_timeseries


def test_itemes_present():
    assert False == _itemes_present(None)
    assert False == _itemes_present({})
    assert False == _itemes_present({"data": {}})
    assert False == _itemes_present({"data": {"items": []}})
    assert True == _itemes_present({"data": {"items": ["something"]}})


def test_x_in_data():
    x = "X"
    not_x = "not_x"
    y = "DATA"
    assert None == _x_in_data(None, x)
    assert None == _x_in_data(False, x)
    assert None == _x_in_data({}, x)
    assert None == _x_in_data({"data": None}, x)
    assert None == _x_in_data({"data": False}, x)
    assert None == _x_in_data({"data": {}}, x)
    assert None == _x_in_data({"data": {"items": None}}, x)
    assert None == _x_in_data({"data": {"items": False}}, x)
    assert None == _x_in_data({"data": {"items": []}}, x)
    assert None == _x_in_data({"data": {"items": [x]}}, x)
    assert None == _x_in_data({"data": {"items": [[x]]}}, x)
    assert y == _x_in_data({"data": {"items": [{x: y}]}}, x)
    assert None == _x_in_data({"data": {"items": [{x: y}]}}, not_x)


def test_id_in_data():
    assert None == _id_in_data(None)
    assert None == _id_in_data({})
    assert None == _id_in_data({"data": None})
    assert None == _id_in_data({"data": {}})
    assert None == _id_in_data({"data": {"bob": "lol"}})
    assert None == _id_in_data({"data": {"items": None}})
    assert None == _id_in_data({"data": {"items": []}})
    assert None == _id_in_data({"data": {"items": [{"ba": "bla"}]}})
    assert None == _id_in_data({"data": {"items": [{"id": None}]}})
    assert "ok" == _id_in_data({"data": {"items": [{"id": "ok"}]}})
    # Also tests _id_in_data


def test_get_items():
    items = _get_items(tsapi_data)
    # logger.info(pprint.pformat(tsapi_data))
    # logger.info(pprint.pformat(items))


def test_transform_from_timeseries_to_gordo():
    gordo_data = transform_from_timeseries_to_gordo(tsapi_datas)
    # logger.info("FROM -------------------------")
    # logger.info(pprint.pformat(tsapi_datas))
    # logger.info("TO ---------------------------")
    # logger.info(pprint.pformat(gordo_data))
    expected_gordo_data = {"X": [[69.69, 42], [42.69, 420], [1337.69, 420]]}
    assert gordo_data == expected_gordo_data
