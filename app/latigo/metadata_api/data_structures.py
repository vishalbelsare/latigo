"""Dataclasses for Time Series ID metadata for sending to the Metadata API."""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Union

from latigo.types import PredictionDataSet


@dataclass
class InputTag:
    """Info about tag(sensor). That tag`s data was taken for the prediction.

    Dataclass attributes:
        name: name if the tag(sensor). Example: "1903.R-29TE3001.MA_Y".
        time_series_id: id from Time Series API of the data for prediction was taken.
    """

    name: str
    time_series_id: str


@dataclass
class OutputTag:
    """Info about tag(sensor). Prediction results metadata.

    Dataclass attributes:
        name: tag(sensor) name that was composed for Time Series ID in Latigo (not tag name itself).
            Examples:
                - "1903.INDICATOR|3c22-b5a0-4a76-99-59c4-9999|total-anomaly-confidence".
                - "1903.R-00AAA0000.MA_Y|3c22-b5a0-4a76-99-59c4-9999|model-output".
            First part is "asset.INDICATOR" for predictions as 'total-anomaly-scaled', 'total-anomaly-confidence', etc.
        time_series_id: id from Time Series API where prediction results were written to.
        type: prediction results type. Could be one of: "aggregated" OR "derived".
        description (optional): short description of the prediction.
        derived_from (optional): input tag name base on what prediction was made.
            It'll be None for such predictions as 'total-anomaly-scaled', 'total-anomaly-confidence', etc.
    """

    name: str
    time_series_id: str
    type: str
    description: str = None
    derived_from: str = None

    def __post_init__(self):
        if self.type not in ["aggregated", "derived"]:
            raise ValueError("'type' attribute can be one of the 'aggregated' or 'derived' values.")

    @staticmethod
    def make_output_tag_type(original_tag_name: str) -> str:
        """Make 'type' for output_tag metadata.

        Args:
            original_tag_name: original tag name that we got from the prediction results.
        """
        return "derived" if original_tag_name else "aggregated"

    @staticmethod
    def make_output_tag_derived_from(tag_name: str) -> Union[str, None]:
        """Make 'derived_from' for output_tag metadata."""
        return tag_name or None

    @staticmethod
    def make_output_tag_description(operation: str, tag_name: str) -> str:
        """Make description for output_tag."""
        return f"Gordo {operation} - {tag_name}"


@dataclass
class TimeSeriesIdMetadata:
    """Metadata about predictions (general info, where data was taken/results written, etc.).

    Dataclass attributes:
        project_name: name of the project what`s data was used from predictions. Example: IOC_000.
        model_name: name of the model. Example: 00000000-0000-0000-0000-db70adcf653d-0000.
        revision: revision(version) of the project/model/etc. that was used in the prediction. Example: 1583238576000
        training_time_from: model training time "from" (should be taken from the .yaml file at "train_start_date").
        training_time_to: model training time "to" (should be taken from the .yaml file at "train_end_date").
        input_tags: Info about tag(sensor). This tag`s data was taken for making the prediction.
        output_tags: info about tag(sensor). Prediction results metadata.
        description (optional): short description.
        status (optional): model status on the training period. Default value is "not_defined".
        labels (optional): this might be used in the next release, useless for now.
    """

    project_name: str
    model_name: str
    revision: str
    training_time_from: datetime
    training_time_to: datetime
    input_tags: List[InputTag]
    output_tags: List[OutputTag]
    description: str = None
    status: str = "not_defined"
    labels: List[str] = None

    @staticmethod
    def make_prediction_metadata_description(prediction_data: PredictionDataSet) -> str:
        """Make description for prediction metadata."""
        return (
            f"Gordo prediction for project '{prediction_data.meta_data.project_name}', "
            f"model '{prediction_data.meta_data.model_name}'. "
            f"Prediction period: from '{prediction_data.time_range.from_time}' : to '{prediction_data.time_range.to_time}'"
        )
