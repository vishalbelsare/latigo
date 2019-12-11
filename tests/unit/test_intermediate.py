import logging
import pprint
import typing
from latigo.intermediate import IntermediateFormat

logger = logging.getLogger(__name__)

# fmt: off
tsapi_data = {
    "data": {
        "items": [
             {
                "id": "c530a095-b86e-4adb-9fae-78b9e3974f48",
                "name": "tag_1",
                "unit": "some_unit_1",
                "datapoints": [
                    {
                        "time": "2019-06-10T21:00:07.616Z",
                        "value": 69.69,
                        "status": 420
                    },
                    {
                        "time": "2019-06-10T21:10:07.616Z",
                        "value": 42.69,
                        "status": 420
                    },
                    {
                        "time": "2019-06-10T21:20:07.616Z",
                        "value": 1337.69,
                        "status": 1337
                    },
                    {
                        "time": "2019-06-10T21:30:07.616Z",
                        "value": 1337.69,
                        "status": 1337
                    }
                ]
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
            {
                "time": "2019-06-10T21:00:07.616Z",
                "value": 69.69,
                "status": 420
            },
            {
                "time": "2019-06-10T21:10:07.616Z",
                "value": 42.69,
                "status": 420
            },
            {
                "time": "2019-06-10T21:20:07.616Z",
                "value": 1337.69,
                "status": 1337
            },
            {
                "time": "2019-06-10T21:30:07.616Z",
                "value": 1337.69,
                "status": 1337
            }
        ]
    },
    {
        "id": "9f9c003c-ab5d-4a25-830c-60fb5499805f",
        "name": "tag_2",
        "unit": "some_unit_2",
        "datapoints": [
            {
                "time": "2019-06-10T21:00:07.616Z",
                "value": 42,
                "status": 69
            },
            {
                "time": "2019-06-10T21:10:07.616Z",
                "value": 420,
                "status": 69
            },
            {
                "time":"2019-06-10T21:20:07.616Z",
                "value": 80085,
                "status": 69
            }
        ]
    }
]

expected_intermediate_tag_names= ['tag_1', 'tag_2']
expected_intermediate_tag_map={'tag_1': 0, 'tag_2': 1}
expected_intermediate_tag_data={'tag_1': [69.69, 42.69, 1337.69, 1337.69], 'tag_2': [42, 420, 80085]}

expected_gordo_data= {'X': [[69.69], [42.69], [1337.69]], 'Y': [[42], [420], [80085]]}
# fmt: on


def test_from_timeseries_to_gordo():
    info = IntermediateFormat()
    info.from_time_series_api(tsapi_datas)
    # logger.info(f"tagnames: {info.tag_names} tagmap {info.tag_names_map} tagdata {info.tag_names_data}")
    assert info.tag_names == expected_intermediate_tag_names
    assert info.tag_names_map == expected_intermediate_tag_map
    assert info.tag_names_data == expected_intermediate_tag_data
    gordo_data = info.to_gordo(tags=["tag_1"], target_tags=["tag_2"])
    # logger.info(f"gordo_data: {gordo_data}")
    assert gordo_data == expected_gordo_data
