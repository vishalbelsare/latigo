import logging
import pprint
import typing

from latigo.intermediate import IntermediateFormat
from latigo.sensor_data import SensorDataProviderInterface
from latigo.types import LatigoSensorTag, SensorDataSet, SensorDataSpec, TimeRange

logger = logging.getLogger(__name__)


class MockSensorDataProvider(SensorDataProviderInterface):
    def __init__(self, config: dict):
        self.config = config
        self.name = config.get("mock_name", "mock_name")
        self.asset_id = config.get("mock_asset_id", "mock_asset_id")
        self.unit = config.get("mock_unit", "mock_unit")
        self.mock_data = config.get("mock_data", [])

    def supports_tag(self, tag: LatigoSensorTag) -> bool:
        return True

    def get_data_for_range(
        self, spec: SensorDataSpec, time_range: TimeRange
    ) -> typing.Tuple[typing.Optional[SensorDataSet], typing.Optional[str]]:
        """
        return the actual data as per the range specified
        """
        if self.mock_data:
            logger.info("MOCK PROVIDING SENSOR DATA:")
            logger.info(pprint.pformat(self.mock_data))
            # data = SensorDataSet(name=mock_name, time_range=time_range, asset_id=mock_asset_id, data=mock_data, unit=mock_unit)
            data = SensorDataSet(time_range=time_range, data=IntermediateFormat())
        return data, None
