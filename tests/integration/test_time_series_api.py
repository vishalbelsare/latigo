import pandas as pd
import typing
import logging
import pprint
from datetime import datetime, timedelta
from os import environ
from collections import namedtuple
from latigo.time_series_api import (
    TimeSeriesAPIClient,
    TimeSeriesAPIPredictionStorageProvider,
    TimeSeriesAPISensorDataProvider,
    IMSMetadataAPIClient,
    _itemes_present,
    _id_in_data,
)
from latigo.types import PredictionDataSet, TimeRange, SensorDataSpec, LatigoSensorTag
from latigo.utils import datetime_from_rfc3339

from latigo.intermediate import IntermediateFormat


logger = logging.getLogger(__name__)


def _get_config():
    not_found = "Not found in environment variables"
    # fmt: off
    return {
        "type": "time_series_api",
        "base_url": "https://api.gateway.equinor.com/plant/timeseries/v1.5", #environ.get("LATIGO_TIME_SERIES_BASE_URL", not_found),
        "ims_meta_base_url": "https://api.gateway.equinor.com/plant-beta/ims-metadata/v1.2", #environ.get("LATIGO_TIME_SERIES_BASE_URL", not_found),
        "ims_subscription_base_url": "https://api.gateway.equinor.com/plant/ims-subscriptions/v1.0", #environ.get("LATIGO_TIME_SERIES_BASE_URL", not_found),
        "async": False,
        "auth": {
            "resource": environ.get("LATIGO_TIME_SERIES_RESOURCE", not_found),
            "tenant": environ.get("LATIGO_TIME_SERIES_TENANT", not_found),
            "authority_host_url": environ.get("LATIGO_TIME_SERIES_AUTH_HOST_URL", not_found),
            "client_id": environ.get("LATIGO_TIME_SERIES_CLIENT_ID", not_found),
            "client_secret": environ.get("LATIGO_TIME_SERIES_CLIENT_SECRET", not_found)
        },
        "ims_meta_auth": {
            "resource": environ.get("LATIGO_TIME_SERIES_IMS_META_RESOURCE", not_found),
            "tenant": environ.get("LATIGO_TIME_SERIES_IMS_META_TENANT", not_found),
            "authority_host_url": environ.get("LATIGO_IMS_TIME_SERIES_META_AUTH_HOST_URL", not_found),
            "client_id": environ.get("LATIGO_TIME_SERIES_IMS_META_CLIENT_ID", not_found),
            "client_secret": environ.get("LATIGO_TIME_SERIES_IMS_META_CLIENT_SECRET", not_found)
        },
        "ims_subscription_auth": {
            "resource": environ.get("LATIGO_TIME_SERIES_IMS_SUBSCRIPTION_RESOURCE", not_found),
            "tenant": environ.get("LATIGO_TIME_SERIES_IMS_SUBSCRIPTION_TENANT", not_found),
            "authority_host_url": environ.get("LATIGO_TIME_SERIES_IMS_SUBSCRIPTION_AUTH_HOST_URL", not_found),
            "client_id": environ.get("LATIGO_TIME_SERIES_IMS_SUBSCRIPTION_CLIENT_ID", not_found),
            "client_secret": environ.get("LATIGO_TIME_SERIES_IMS_SUBSCRIPTION_CLIENT_SECRET", not_found)
        },
        
    }
    # fmt: on


name: str = "latigo_integration_name_test"
name2: str = "latigo_integration_name_test_with_appendage"
asset: str = "latigo_integration_asset_test"
datapoint_1 = 1337.0
datapoint_2 = 69.69
datapoint_3 = 420.42
time_1 = "2019-12-09T10:37:51.810Z"
time_2 = "2019-12-09T11:37:51.810Z"
time_3 = "2019-12-09T12:37:51.810Z"
unit: str = "Tesla"

im1 = IntermediateFormat()
# fmt: off
data1 = [{'tag':name, 'value':datapoint_1, 'time':time_1},
        {'tag':name, 'value':datapoint_2, 'time':time_2},
        {'tag':name, 'value':datapoint_3, 'time':time_3}]
data1_wrapped={"data": {"items": data1}}
# fmt: on
im1.from_time_series_api(data1)

im2 = IntermediateFormat()
# fmt: off
data2 = [{'tag':name2, 'value':datapoint_1, 'time':time_1},
        {'tag':name2, 'value':datapoint_2, 'time':time_2},
        {'tag':name2, 'value':datapoint_3, 'time':time_3}]
data2_wrapped={"data": {"items": data2}}
# fmt: on
im2.from_time_series_api(data2)


from_time = datetime_from_rfc3339("2019-01-02T00:00:00Z")
to_time = datetime_from_rfc3339("2019-11-02T00:00:00Z")
time_range = TimeRange(from_time=from_time, to_time=to_time)

# fmt: off
tag_list = [
LatigoSensorTag(
    name=name,
    asset=asset),
LatigoSensorTag(
    name="tag_name_2",
    asset="tag_asset_2")
]
# fmt: on

spec: SensorDataSpec = SensorDataSpec(tag_list=tag_list)

# actual_tag_list = [LatigoSensorTag(name="GRA-STAT-20-1310_G01.ST", asset="1755-gra")]
# actual_tag_list = [LatigoSensorTag(name="GRA-FOI -13-0979.PV", asset="GRA")]
actual_tag_list = [LatigoSensorTag(name="PT-13005/MeasA/PRIM", asset="1101-sfb")]
# ioc-preprod.ginkgrog-b17

#'PT-13005/MeasA/PRIM', asset='1101-sfb'), SensorTag(name='TT-13092/Meas1/PRIM', asset='1101-sfb'), Sen..., SensorTag(name='DQ-TT-T-B30L/Meas1/PRIM', asset='1101-sfb'), SensorTag(name='PT-13009/MeasA/PRIM', asset='1101-sfb')

actual_spec: SensorDataSpec = SensorDataSpec(tag_list=actual_tag_list)
# , ("GRA-HIC -13-0035.PV", "1755-gra")]


def test_time_series_api_get_meta_by_name():
    items = {
        "latigo_integration_name_test": "92e41ea1-b2eb-43d1-b629-4d547cd29a45",
        "latigo_integration_name_test_not_exist": None,
    }
    tsac = TimeSeriesAPIClient(config=_get_config())
    for name, id in items.items():
        meta, err = tsac._get_meta_by_name(name)
        if meta:
            found_id = _id_in_data(meta)
        if not id:
            assert None == found_id
        else:
            assert id == found_id
            assert None == err


# Test data is in wrong format, disabling this test
def test_time_series_api_write_read():
    config = _get_config()
    logger.info("")
    logger.info("WRITING ---------------")
    prediction_storage_provider = TimeSeriesAPIPredictionStorageProvider(config)
    meta_data = {"unit": unit, "asset_id": asset, "name": name}
    prediction_data = PredictionDataSet(
        time_range=time_range, data=data1_wrapped, meta_data=meta_data
    )
    meta = prediction_storage_provider.put_predictions(prediction_data=prediction_data)
    logger.info(pprint.pformat(meta))
    logger.info("")
    logger.info("READING ---------------")
    sensor_data_provider = TimeSeriesAPISensorDataProvider(config)
    sensor_data = sensor_data_provider.get_data_for_range(
        spec=spec, time_range=time_range
    )


def test_time_series_api_actual_read():
    sensor_data_provider = TimeSeriesAPISensorDataProvider(_get_config())
    sensor_data = sensor_data_provider.get_data_for_range(
        spec=actual_spec, time_range=time_range
    )
    logger.info(pprint.pformat(sensor_data))


def test_get_meta_by_name():
    tsac = TimeSeriesAPIClient(config=_get_config())
    # input = {"name": "GRA-TIT -23-0615.PV", "asset_id": "1755-gra"}
    input = {"name": "PT-13005/MeasA/PRIM", "asset_id": "1101-sfb"}
    logger.info("WITH: ")
    logger.info(pprint.pformat(input))
    # res = tsac._get_id_by_name(name=input.get("name"), asset_id=input.get("asset_id"))
    meta = tsac._get_meta_by_name(name=input.get("name"))
    logger.info("GOT: ")
    logger.info(pprint.pformat(meta))


# IMS metadata api is not in use so this test is disabled
def un_test_ims_metadata_api():
    ims_meta = IMSMetadataAPIClient(_get_config())
    tag_name = "GRA-STAT-20-1310_G01.ST"
    system_code = ims_meta._get_system_code_by_tag_name(tag_name=tag_name)
    logger.info(f"System code for tag '{tag_name}' is '{system_code}'")


# Test data is in wrong format, disabling this test
def test_name_lookup_bug1():
    config = _get_config()
    logger.info("")
    logger.info("WRITING Data 1 ---------------")
    prediction_storage_provider = TimeSeriesAPIPredictionStorageProvider(config)
    name = "an inconspicuous tag name"
    in_meta = {"name": name, "unit": unit, "asset_id": asset}
    prediction_data = PredictionDataSet(
        meta_data=in_meta, time_range=time_range, data=data1_wrapped
    )
    out_meta1 = prediction_storage_provider.put_predictions(
        prediction_data=prediction_data
    )
    logger.info(pprint.pformat(out_meta1))
    logger.info("")
    logger.info("WRITING Data 2 ---------------")
    name2 = f"{name}_with_apendage"
    in_meta2 = {"name": name2, "unit": unit, "asset_id": asset}
    prediction_data2 = PredictionDataSet(
        meta_data=in_meta2, time_range=time_range, data=data2_wrapped
    )
    out_meta2 = prediction_storage_provider.put_predictions(
        prediction_data=prediction_data2
    )
    logger.info(pprint.pformat(out_meta2))
    logger.info("")
    logger.info("READING ---------------")
    sensor_data_provider = TimeSeriesAPISensorDataProvider(config)
    sensor_data = sensor_data_provider.get_data_for_range(
        spec=spec, time_range=time_range
    )
