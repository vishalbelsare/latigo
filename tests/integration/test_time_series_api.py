import pandas as pd
import typing
import logging
import pprint
from datetime import datetime, timedelta
from os import environ
from collections import namedtuple
from latigo.time_series_api import TimeSeriesAPIClient, TimeSeriesAPIPredictionStorageProvider, TimeSeriesAPISensorDataProvider, IMSMetadataAPIClient, _itemes_present, _id_in_data
from latigo.types import PredictionData, TimeRange, SensorDataSpec, LatigoSensorTag
from latigo.utils import datetime_from_rfc3339


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


name: str = "latigo_integration_test"
from_time = datetime_from_rfc3339("2019-01-02T00:00:00Z")
to_time = datetime_from_rfc3339("2019-11-02T00:00:00Z")
time_range = TimeRange(from_time=from_time, to_time=to_time)

tag_list = [LatigoSensorTag(name="tag_name_1", asset="tag_asset_1"), LatigoSensorTag(name="tag_name_2", asset="tag_asset_2")]
spec: SensorDataSpec = SensorDataSpec(tag_list=tag_list)

# actual_tag_list = [LatigoSensorTag(name="GRA-STAT-20-1310_G01.ST", asset="1755-gra")]
# actual_tag_list = [LatigoSensorTag(name="GRA-FOI -13-0979.PV", asset="GRA")]
actual_tag_list = [LatigoSensorTag(name="PT-13005/MeasA/PRIM", asset="1101-sfb")]
#ioc-preprod.ginkgrog-b17

#'PT-13005/MeasA/PRIM', asset='1101-sfb'), SensorTag(name='TT-13092/Meas1/PRIM', asset='1101-sfb'), Sen..., SensorTag(name='DQ-TT-T-B30L/Meas1/PRIM', asset='1101-sfb'), SensorTag(name='PT-13009/MeasA/PRIM', asset='1101-sfb')

actual_spec: SensorDataSpec = SensorDataSpec(tag_list=actual_tag_list)
# , ("GRA-HIC -13-0035.PV", "1755-gra")]

data: typing.Iterable[typing.Tuple[str, pd.DataFrame, typing.List[str]]] = []


def disabled_test_time_series_api_write():
    prediction_storage_provider = TimeSeriesAPIPredictionStorageProvider(_get_config())
    prediction_data = PredictionData(name=name, time_range=time_range, data=data)
    prediction_storage_provider.put_predictions(prediction_data)


def disabled_test_time_series_api_read():
    sensor_data_provider = TimeSeriesAPISensorDataProvider(_get_config())
    sensor_data = sensor_data_provider.get_data_for_range(spec=spec, time_range=time_range)


def disabled_test_time_series_api_actual_read():
    sensor_data_provider = TimeSeriesAPISensorDataProvider(_get_config())
    sensor_data = sensor_data_provider.get_data_for_range(spec=actual_spec, time_range=time_range)
    logger.info(pprint.pformat(sensor_data))


def test_get_id_by_name():
    tsac = TimeSeriesAPIClient(config=_get_config())
    #input = {"name": "GRA-TIT -23-0615.PV", "asset_id": "1755-gra"}
    input = {"name": "PT-13005/MeasA/PRIM", "asset_id": "1101-sfb"}
    logger.info("WITH: ")
    logger.info(pprint.pformat(input))
    #res = tsac._get_id_by_name(name=input.get("name"), asset_id=input.get("asset_id"))
    res = tsac._get_id_by_name(name=input.get("name"))
    logger.info("GOT: ")
    logger.info(pprint.pformat(res))


def disabled_test_ims_metadata_api():
    ims_meta = IMSMetadataAPIClient(_get_config())
    tag_name = "GRA-STAT-20-1310_G01.ST"
    system_code = ims_meta._get_system_code_by_tag_name(tag_name=tag_name)
    logger.info(f"System code for tag '{tag_name}' is '{system_code}'")
