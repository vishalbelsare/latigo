import logging
import typing

from latigo.sensor_data import SensorDataProviderInterface
from latigo.types import LatigoSensorTag, SensorDataSet, SensorDataSpec, TimeRange

from ..log import measure
from .client import TimeSeriesAPIClient

logger = logging.getLogger(__name__)


def _find_tag_in_data(res, tag):
    if not isinstance(res, dict):
        return None
    data = res.get("data", {})
    if not isinstance(data, dict):
        return None
    items = data.get("items", [])
    if not isinstance(items, list):
        return None
    if len(items) < 1:
        return None
    for item in items:
        if not isinstance(item, dict):
            continue

        name = item.get("name", None)
        if not name:
            continue
        if tag == name:
            return item
    return None


class TimeSeriesAPISensorDataProvider(TimeSeriesAPIClient, SensorDataProviderInterface):
    def __init__(self, config: dict):
        super().__init__(config)
        self._parse_auth_config()
        self._parse_base_url()

    def __str__(self):
        return f"TimeSeriesAPISensorDataProvider({self.base_url})"

    @measure("get_data_for_range")
    def get_data_for_range(
        self, spec: SensorDataSpec, time_range: TimeRange
    ) -> typing.Tuple[typing.Optional[SensorDataSet], typing.Optional[str]]:
        """Fetch sensor data from TS API per the range.

        This func uses less calls to fetch the data: 1 call per 100 tags.

        Note: do not use "tag.asset" in calls to the TS API.
            It's provided by user OR Gordo and not compatible with TS.
        """
        tag_list: typing.List[LatigoSensorTag] = spec.tag_list

        tag_ids_names: typing.Dict[str, str] = {}
        common_facility = self.get_facility_by_tag_name(tag_name=tag_list[0].name)
        for raw_tag in tag_list:
            tag: LatigoSensorTag = raw_tag
            name = tag.name
            meta = self.get_meta_by_name(name=name, facility=common_facility)
            if not meta:
                raise ValueError("'meta' was not found for name '%s' and facility '%s'", name, common_facility)

            item = _find_tag_in_data(meta, name)
            tag_ids_names[item["id"]] = name

        tags_data = self._fetch_data_for_multiple_ids(tag_ids=list(tag_ids_names), time_range=time_range)
        empty_tags_ids = [tag_data["id"] for tag_data in tags_data if not tag_data.get("datapoints", None)]

        if empty_tags_ids:
            tags_data = [tag for tag in tags_data if tag["id"] not in empty_tags_ids]
            logger.warning("'datapoints' are empty for the following tags: %s", "; ".join(empty_tags_ids))

        if not tags_data:
            raise ValueError("No datapoints for tags where found.")

        for tag_data in tags_data:  # add "tag_name" to data cause TS API does not return it anymore
            tag_id = tag_data["id"]
            tag_data["name"] = tag_ids_names[tag_id]

        dataframes = SensorDataSet.to_gordo_dataframe(tags_data, time_range.from_time, time_range.to_time)
        return SensorDataSet(time_range=time_range, data=dataframes), None
