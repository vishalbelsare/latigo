import time
import typing
import logging
import pandas as pd
from datetime import datetime

from latigo.types import TimeRange, LatigoSensorTag, SensorDataSet
from latigo.sensor_data import SensorDataProviderInterface
from latigo.types import SensorDataSpec

from gordo.machine.dataset.data_provider.base import GordoBaseDataProvider
from gordo.machine.dataset.sensor_tag import SensorTag
from gordo.util.utils import capture_args

logger = logging.getLogger(__name__)
# logging.getLogger().setLevel(logging.WARNING)


def _gordo_to_latigo_tag(gordo_tag: SensorTag) -> LatigoSensorTag:
    latigo_tag = LatigoSensorTag(gordo_tag.name, gordo_tag.asset)
    return latigo_tag


def _gordo_to_latigo_tag_list(
    gordo_tag_list: typing.List[SensorTag],
) -> typing.List[LatigoSensorTag]:
    latigo_tag_list: typing.List[LatigoSensorTag] = []
    for gordo_tag in gordo_tag_list:
        latigo_tag = _gordo_to_latigo_tag(gordo_tag)
        latigo_tag_list.append(latigo_tag)
    return latigo_tag_list


class LatigoDataProvider(GordoBaseDataProvider):
    """
    A GordoBaseDataProvider that wraps Latigo spesific data providers
    """

    @capture_args
    def __init__(
        self,
        config: dict,
        sensor_data_provider: typing.Optional[SensorDataProviderInterface],
    ):
        super().__init__()
        self.latigo_config = config
        if self == config:
            raise Exception("Config was self")
        if type(config) == type(self):
            raise Exception(f"Config was same type as self {type(self)}")
        if not self.latigo_config:
            raise Exception("No data_provider_config specified")
        self.sensor_data_provider = sensor_data_provider
        # logger.warning("DEBUGGING:")         logger.warning(config)        logger.error("".join(traceback.format_stack()))

    def load_series(
        self,
        train_start_date: datetime,
        train_end_date: datetime,
        tag_list: typing.List[SensorTag],
        dry_run: typing.Optional[bool] = False,
    ) -> typing.Iterable[pd.Series]:
        if dry_run:
            raise NotImplementedError(
                "Dry run for LatigoDataProvider is not implemented"
            )
        if not tag_list:
            logger.warning(
                "LatigoDataProvider called with empty tag_list, returning none"
            )
            return
        if train_end_date < train_start_date:
            raise ValueError(
                f"LatigoDataProvider called with to_ts: {train_end_date} before from_ts: {train_start_date}"
            )
        if not self.sensor_data_provider:
            logger.warning("Skipping, no sensor_data_provider")
            return
        spec: SensorDataSpec = SensorDataSpec(
            tag_list=_gordo_to_latigo_tag_list(tag_list)
        )
        time_range = TimeRange(from_time=train_start_date, to_time=train_end_date)
        sensor_data, err = self.sensor_data_provider.get_data_for_range(
            spec, time_range
        )
        if err:
            logger.error(f"Could not load sensor data: {err}")
            return
        if not sensor_data:
            logger.error(f"No sensor data")
            return
        if not sensor_data.ok():
            logger.error(f"Sensor data not OK")
            return
        if not sensor_data.data:
            logger.error(f"No data.data")
            return

        if not sensor_data.data:
            logger.error(f"No gordo data")
            return

        for d in sensor_data.data:
            yield d
        return

    def can_handle_tag(self, tag: SensorTag) -> bool:
        if self.sensor_data_provider:
            if self.sensor_data_provider:
                return self.sensor_data_provider.supports_tag(tag=tag)
        return False

    def __repr__(self):
        return f"LatigoDataProvider(config={self.latigo_config}, sensor_data_provider={self.sensor_data_provider})"
