import logging
import math
from typing import Dict, Tuple

from requests.exceptions import HTTPError

from latigo.metadata_api.data_structures import OutputTag
from latigo.prediction_storage import PredictionStorageProviderInterface
from latigo.log import measure
from latigo.types import PredictionDataSet
from latigo.utils import rfc3339_from_datetime

from .client import TimeSeriesAPIClient
from .misc import INVALID_OPERATIONS, get_time_series_id_from_response, prediction_data_naming_convention

logger = logging.getLogger(__name__)


class TimeSeriesAPIPredictionStorageProvider(TimeSeriesAPIClient, PredictionStorageProviderInterface):
    def __init__(self, config: dict):
        super().__init__(config)

    def __str__(self):
        return f"TimeSeriesAPIPredictionStorageProvider({self.base_url})"

    @measure("storing_prediction_data")
    def put_prediction(self, prediction_data: PredictionDataSet):
        """Store prediction data in time series api.

        Args:
            prediction_data: dataframe as a result of prediction execution and prediction metadata.

        Take into account:
            - do not rely on the Gordo asset;
            - fetch facility from first "input tag" (they all are from
                the same facility) in TS API.
            - use such facility for caching/adding new prediction-tags.

        Raises:
            - Exception: if more then one prediction in "prediction_data.data" were passed.
            - ValueError: if no tag items were found.
            - ValueError: if more then one tag with such name were found.
            - ValueError: if 'facility' is missing.
            - ValueError: no tag was found in the dataframe columns.
        """
        data = prediction_data.data
        if not data:
            logger.warning("No prediction data for storing")
            return None
        if len(data) > 1:
            raise Exception(f"Only one prediction could be passed for storing, but passed - '{len(data)}'")

        # output_tag_names: ('model-output', '1903.R-29L.MA_Y'): '1903.R-29LT.MA_Y|24ae-6d22-a6-b8-337-999|model-output'
        output_tag_names: Dict[Tuple[str, str], str] = {}
        # "output_time_series_ids": ('model-output', '1903.R-29LT1047.MA_Y'): '73ef5e6c-9142-4127-be64-a68e6916'
        output_time_series_ids: Dict[Tuple[str, str], str] = {}
        model_name = prediction_data.meta_data.model_name
        row = data[0]
        df = row[1]

        first_not_empty_tag = next((tag_name for _, tag_name in df.columns if tag_name), None)
        if first_not_empty_tag is None:
            raise ValueError(f"No tag was found in the dataframe columns {df.columns}")
        common_facility = self.get_facility_by_tag_name(tag_name=first_not_empty_tag)

        for col in df.columns:
            operation = col[0]
            tag_name = col[1]

            output_tag_name = prediction_data_naming_convention(
                operation=operation, model_name=model_name, tag_name=tag_name, facility=common_facility
            )
            if not output_tag_name:
                continue
            output_time_series_ids[col] = ""
            description = OutputTag.make_output_tag_description(operation, tag_name)
            try:
                meta = self._create_id_if_not_exists(
                    name=output_tag_name, description=description, facility=common_facility,
                )
            except HTTPError as error:
                if error.response.status_code != 409:
                    raise

                # if such tag_name might already exists in the TS try to get/create once more.
                meta = self.replace_cached_metadata_with_new(
                    tag_name=output_tag_name, facility=common_facility, description=description
                )

            if not meta:
                raise ValueError(f"Could not create/find id for name {output_tag_name}, {col}, {meta}")
            time_series_id = get_time_series_id_from_response(meta)
            if not time_series_id:
                raise ValueError(f"Could not get ID for {output_tag_name}, {col}, {meta}")
            output_tag_names[col] = output_tag_name
            output_time_series_ids[col] = time_series_id
        skipped_values = 0
        stored_values = 0
        skipped_tags = 0
        logger.info(f"Storing predictions for %s columns (before filtering)", len(df.columns))

        datapoints_to_store = []
        for key, item in df.items():
            operation, tag_name, *_ = key
            if operation in INVALID_OPERATIONS:
                continue
            datapoints = []
            time_series_id = output_time_series_ids[key]
            if not time_series_id:
                raise ValueError(f"Time Series ID for prediction storing was not found: key - '{key}'")

            for time, value in item.items():
                if math.isnan(value):
                    skipped_values += 1
                    continue
                stored_values += 1
                datapoints.append({"time": rfc3339_from_datetime(time), "value": value, "status": "0"})

            if not datapoints:  # skip empty datapoints, no need make call to TS API with no data to store
                skipped_tags += 1
                continue
            datapoints_to_store.append({"id": time_series_id, "datapoints": datapoints})

        res = self.store_multiple_datapoints(datapoints_to_store)
        if skipped_values:
            logger.warning(
                f"[Not all data stored to TS API] {stored_values} values stored, {skipped_values} NaNs skipped. "
                f"{skipped_tags} tags skipped. Storing results: {res['message']}"
            )

        return output_tag_names, output_time_series_ids
