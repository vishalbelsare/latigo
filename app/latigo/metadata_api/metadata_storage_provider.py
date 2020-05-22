import logging
from typing import Dict, Tuple

from latigo.log import measure
from latigo.metadata_api.client import MetadataAPIClient
from latigo.metadata_api.data_structures import InputTag, OutputTag, TimeSeriesIdMetadata
from latigo.metadata_storage import MetadataStorageProviderInterface
from latigo.time_series_api.misc import DATES_OPERATIONS, MODEL_INPUT_OPERATION
from latigo.types import PredictionDataSet

logger = logging.getLogger(__name__)


class MetadataAPIMetadataStorageProvider(MetadataAPIClient, MetadataStorageProviderInterface):
    def __str__(self):
        return f"<{ type(self).__name__ }: { self.base_url }>"

    @measure("store_prediction_metadata")
    def put_prediction_metadata(
        self,
        prediction_data: PredictionDataSet,
        output_tag_names: Dict[Tuple[str, str], str],
        output_time_series_ids: Dict[Tuple[str, str], str],
        input_time_series_ids: Dict[str, str],
    ):
        """Store metadata of the already made and stored prediction.

        Args:
            prediction_data: dataframe as a result of prediction execution and prediction metadata.
            output_tag_names: tag names in Time Series API for relevant tag_names.
                Example: ('model-output', '1903.R-29LT10.MA_Y'): '1903.R-29LT.MA_Y|24ae-22-a6-b8-337-999|model-output'.
            output_time_series_ids: Time Series IDs for relevant tag_names.
                Example: ('tag-anomaly-scaled', '1903.R-29LT10.MA_Y'): '73ef5e6c-9142-4127-be64-a68e6916'.
            input_time_series_ids: input tag_names with relevant Time Series IDs.
                Example: {tag_name: time_series_id}.
        """
        metadata_api_input_tags = []
        metadata_api_output_tags = []
        df_columns = prediction_data.data[0][1].columns

        project_name = prediction_data.meta_data.project_name
        revision = prediction_data.meta_data.revision
        model_name = prediction_data.meta_data.model_name
        model_training_period = prediction_data.meta_data.model_training_period

        # fill the tags
        for col in df_columns:
            operation, tag_name, *_ = col
            # example: operation: "start", "end", "model-input"; tag_name:  "1903.R-29TT3018.MA_Y"

            if operation == MODEL_INPUT_OPERATION:
                tag_time_series_id = input_time_series_ids[tag_name]
                metadata_api_input_tags.append(InputTag(name=tag_name, time_series_id=tag_time_series_id))
            elif operation not in DATES_OPERATIONS:
                metadata_api_output_tags.append(
                    OutputTag(
                        name=output_tag_names[col],
                        time_series_id=output_time_series_ids[(operation, tag_name)],
                        type=OutputTag.make_output_tag_type(tag_name),
                        derived_from=OutputTag.make_output_tag_derived_from(tag_name),
                        description=OutputTag.make_output_tag_description(operation, tag_name),
                    )
                )
            else:
                continue

        ts_metadata = TimeSeriesIdMetadata(
            project_name=project_name,
            model_name=model_name,
            revision=revision,
            description=TimeSeriesIdMetadata.make_prediction_metadata_description(prediction_data),
            training_time_from=model_training_period.train_start_date,
            training_time_to=model_training_period.train_end_date,
            labels=None,
            input_tags=metadata_api_input_tags,
            output_tags=metadata_api_output_tags,
        )
        res = self.send_time_series_id_metadata(ts_metadata)
        res.raise_for_status()

        logger.info(
            f"[MODEL_ID] Prediction metadata was stored to the Metadata API. " f"Record ID - '{res.json()['model_id']}'"
        )
