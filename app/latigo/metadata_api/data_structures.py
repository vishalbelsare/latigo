"""Dataclasses for Time Series ID metadata for sending to the Metadata API."""
from dataclasses import dataclass
from datetime import datetime
from typing import List


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
        name: name if the tag(sensor). Example: "1903.R-29TE3001.MA_Y".
        time_series_id: id from Time Series API where prediction results were written to.
        type: prediction results type. Could be one of: "aggregated" OR "derived".
        description (optional): short description of the prediction.
        derived_from (optional): input tag name base on what prediction was made.
            It'll be empty for such predictions as 'total-anomaly-scaled', 'total-anomaly-confidence', etc.
    """

    name: str
    time_series_id: str
    type: str
    description: str = None
    derived_from: str = None

    def __post_init__(self):
        if self.type not in ["aggregated", "derived"]:
            raise ValueError("'type' attribute can be one of the 'aggregated' or 'derived' values.")


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
