import typing
import random
import logging
import pprint
import numpy as np
import pandas as pd
from datetime import datetime
from .. import PredictionExecutionProviderInterface

from gordo_components.data_provider.base import GordoBaseDataProvider, capture_args
from gordo_components.client.forwarders import PredictionForwarder
from gordo_components.client import Client
from gordo_components.dataset.sensor_tag import SensorTag

from latigo.sensor_data import SensorData, PredictionData
from latigo.utils import parse_event_hub_connection_string
from latigo.event_hub.receive import EventReceiveClient

logger = logging.getLogger(__name__)


class LatigoDataProvider(GordoBaseDataProvider):
    """
    A GordoBaseDataset that wraps Latigo spesific data providers
    """
    @capture_args
    def __init__(self, data_provider_config):
        super().__init__()
        self.data_provider_config=data_provider_config
        if not self.data_provider_config:
            raise Exception("No data_provider_config specified")
        data_provider_type = self.data_provider_config.get("type", None)
        self.data_provider=None
        if "random" == data_provider_type:
            self.data_provider = RandomDataProvider(**data_provider_config)
        elif "influx" == data_provider_type:
            self.data_provider = InfluxDataProvider(**data_provider_config)
        elif "datalake" == data_provider_type:
            self.data_provider = DataLakeProvider(**data_provider_config)

    def load_series(self, from_ts: datetime, to_ts: datetime, tag_list: typing.List[SensorTag], dry_run: typing.Optional[bool] = False) -> typing.Iterable[pd.Series]:
        if self.data_forwarder:
            yield from self.data_forwarder.load_series(from_ts, to_ts, tag_list, dry_run)

    def can_handle_tag(self, tag: SensorTag) -> bool:
        if self.data_forwarder:
            return self.data_forwarder.can_handle_tag(tag)
        return False


class LatigoPredictionForwarder(PredictionForwarder):
    """
    A Gordo PredictionForwarder that wraps Latigo spesific prediction forwarders
    """

    def __init__(self, prediction_forwarder_config):
        super().__init__()
        self.prediction_forwarder_config=prediction_forwarder_config
        if not self.prediction_forwarder_config:
            raise Exception("No prediction_forwarder_config specified")
        prediction_forwarder_type = self.prediction_forwarder_config.get("type", None)
        self.prediction_forwarder=None
        if "random" == prediction_forwarder_type:
            self.prediction_forwarder = RandomDataProvider(**prediction_forwarder_config)
        elif "influx" == prediction_forwarder_type:
            self.prediction_forwarder = InfluxDataProvider(**prediction_forwarder_config)
        elif "datalake" == prediction_forwarder_type:
            self.prediction_forwarder = DataLakeProvider(**prediction_forwarder_config)

        self.parts = parse_event_hub_connection_string(connection_string)


class GordoPredictionExecutionProvider(PredictionExecutionProviderInterface):
    def __init__(self, config):
        self.config = config
        if not self.config:
            raise Exception("No predictor_config specified")
        # TODO: How to model gordo spesific input and output vs our clean interface?
        self.data_provider_config = config.get("data_provider", {})
        if not self.data_provider_config:
            raise Exception("No data_provider_config specified")
        self.prediction_forwarder_config = config.get("prediction_forwarder", {})
        if not self.prediction_forwarder_config:
            raise Exception("No prediction_forwarder_config specified")
        # Augment config with the latigo data provider and prediction forwarders
        self.config["data_provider"] = LatigoDataProvider(data_provider_config)
        self.config["prediction_forwarder"] = LatigoPredictionForwarder(prediction_forwarder_config)
        self.client = Client(**config)

    def execute_prediction(self, prediction_name: str, data: SensorData) -> PredictionData:
        result = self.client.predict(data.time_range.from_time, data.time_range.to_time)
        pd = PredictionData(name=prediction_name, time_range=data.time_range, result=result)
        return pd
