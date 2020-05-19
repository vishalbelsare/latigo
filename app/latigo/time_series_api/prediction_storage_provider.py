import logging
import math
from typing import Dict, Tuple

from latigo.metadata_api.data_structures import OutputTag
from latigo.prediction_storage import PredictionStorageProviderInterface
from latigo.types import PredictionDataSet
from latigo.utils import rfc3339_from_datetime

from .client import TimeSeriesAPIClient
from .misc import (INVALID_OPERATIONS, get_common_asset_id,
                   get_time_series_id_from_response, prediction_data_naming_convention)

logger = logging.getLogger(__name__)


class TimeSeriesAPIPredictionStorageProvider(
    TimeSeriesAPIClient, PredictionStorageProviderInterface
):
    def __init__(self, config: dict):
        super().__init__(config)

    def __str__(self):
        return f"TimeSeriesAPIPredictionStorageProvider({self.base_url})"

    def put_prediction(self, prediction_data: PredictionDataSet):
        """Store prediction data in time series api.

        Args:
            prediction_data: dataframe as a result of prediction execution and prediction metadata.

        Raises:
            Exception: if more then one prediction in "prediction_data.data" were passed.
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
        common_asset_id = get_common_asset_id(df.columns)

        for col in df.columns:
            operation = col[0]
            tag_name = col[1]

            output_tag_name = prediction_data_naming_convention(
                operation=operation, model_name=model_name, tag_name=tag_name, common_asset_id=common_asset_id
            )
            if not output_tag_name:
                continue
            output_time_series_ids[col] = ""
            description = OutputTag.make_output_tag_description(operation, tag_name)
            # Units cannot be derrived easily. Should be provided by prediction execution provider or set to none
            unit = ""
            external_id = ""
            meta, err = self._create_id_if_not_exists(
                name=output_tag_name,
                description=description,
                unit=unit,
                external_id=external_id,
            )
            if (not meta and not err) or err:
                raise ValueError(f"Could not create/find id for name {output_tag_name}, {col}, {meta}, {err}")
            time_series_id = get_time_series_id_from_response(meta)
            if not time_series_id:
                raise ValueError(f"Could not get ID for {output_tag_name}, {col}, {meta}, {err}")
            output_tag_names[col] = output_tag_name
            output_time_series_ids[col] = time_series_id
        failed_tags = 0
        stored_tags = 0
        skipped_values = 0
        stored_values = 0
        logger.info(f"Storing {len(df.columns)} predictions:")
        for key, item in df.items():
            operation, tag_name, *_ = key
            if operation in INVALID_OPERATIONS:
                continue
            datapoints = []
            time_series_id = output_time_series_ids[key]
            if not time_series_id:
                raise ValueError(f"Time Series ID for prediction storing was not found: key - '{key}'")

            for time, value in item.items():
                stored_values += 1
                # logger.info(f"  Item({time}, {value})")
                if math.isnan(value):
                    # logger.info(f"Skipping NaN value for {key} @ {time}")
                    skipped_values += 1
                    continue
                datapoints.append(
                    {"time": rfc3339_from_datetime(time), "value": value, "status": "0"}
                )
            res, err = self._store_data_for_id(id=time_series_id, datapoints=datapoints)
            if not res or err:
                logger.error(f" Could not store data: {err}")
                failed_tags += 1
            else:
                stored_tags += 1

        if skipped_values or failed_tags:
            logger.warning(
                f"[Not all data stored to TS API] {stored_values} values stored, {skipped_values} NaNs skipped. "
                f"{stored_tags} tags stored, {failed_tags} tags failed"
            )

        return output_tag_names, output_time_series_ids
