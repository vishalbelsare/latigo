import logging
import typing

from latigo.types import LatigoSensorTag, SensorDataSet, SensorDataSpec, TimeRange

logger = logging.getLogger(__name__)


class SensorDataProviderInterface:
    def supports_tag(self, tag: LatigoSensorTag) -> bool:
        raise NotImplementedError()

    def get_data_for_range(
        self, spec: SensorDataSpec, time_range: TimeRange
    ) -> typing.Tuple[typing.Optional[SensorDataSet], typing.Optional[str]]:
        """
        return the actual data as per the range specified
        """
        raise NotImplementedError()


def sensor_data_provider_factory(sensor_data_provider_config):
    sensor_data_provider_type = sensor_data_provider_config.get("type", None)

    if "time_series_api" == sensor_data_provider_type:
        from latigo.time_series_api import TimeSeriesAPISensorDataProvider

        sensor_data_provider = TimeSeriesAPISensorDataProvider(sensor_data_provider_config)
    else:
        raise ValueError(f"'{sensor_data_provider_type}' in not valid sensor data provider type")
    return sensor_data_provider
