import typing
import random
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


class TimeSeriesPredictionForwarder(PredictionForwarder):
    """
    To be used as a 'forwarder' for the gordo prediction client
    After instantiation, it is a coroutine which accepts prediction dataframes
    which it will pass onto time series api via event hub
    """

    def __init__(self, connection_string: str, partition: typing.Optional[str] = "0", debug: bool = False, n_retries=5):
        """
        Create an instance which, when called, is a coroutine capable of
        being sent dataframes generated from the '/anomaly/prediction' endpoint
        Parameters
        ----------
        connection_string: str
        Connection string for destination event hub -
        format: Endpoint=sb://<endpoint>/;SharedAccessKeyName=<shared_access_key_name>;SharedAccessKey=<shared_access_key>;EntityPath=<entity_path>
        (copy-pastable from azure eventhub admin panel)
        partition: str
        Specifies which partition into which data will be submitted using event hub API
        debug: bool
        Put event hub into debugging mode (traces data in log)
        """
        self.parts = parse_event_hub_connection_string(connection_string)


class TimeSeriesDataProvider(GordoBaseDataProvider):
    """
    Get a GordoBaseDataset which returns unstructed values for X and y. Each instance
    uses the same seed, so should be a function (same input -> same output)
    """

    @capture_args
    def __init__(self, connection_string: str, debug: bool, n_retries: int, **kwargs):
        super().__init__(**kwargs)
        self.connection_string = connection_string
        self.debug = debug
        self.min_size = 0.0
        self.max_size = 1.0
        self.receiver = None

    # Thanks stackoverflow
    # https://stackoverflow.com/questions/50559078/generating-random-dates-within-a-given-range-in-pandas
    @staticmethod
    def _random_dates(start, end, n: int = 10):
        start = pd.to_datetime(start)
        end = pd.to_datetime(end)
        start_u = start.value // 10 ** 9
        end_u = end.value // 10 ** 9

        return sorted(pd.to_datetime(int(np.random.randint(int(start_u), int(end_u), n)), unit="s", utc=True))

    def can_handle_tag(self, tag: SensorTag):
        return True

    def load_series(self, from_ts: datetime, to_ts: datetime, tag_list: typing.List[SensorTag], dry_run: typing.Optional[bool] = False) -> typing.Iterable[pd.Series]:
        if dry_run:
            raise NotImplementedError("Dry run for TimeSeriesDataProvider is not implemented")
        self.receiver = EventReceiveClient(self.connection_string, self.debug)
        for tag in tag_list:
            nr = int(random.randint(int(self.min_size), int(self.max_size)))

            random_index = self._random_dates(from_ts, to_ts, n=nr)
            series = pd.Series(index=random_index, name=tag.name, data=np.random.random(size=len(random_index)))
        yield series


class GordoPredictionExecutionProvider(PredictionExecutionProviderInterface):
    def __init__(self, config):
        self.predictor_config = self.config.get("predictor", None)
        if not self.predictor_config:
            raise Exception("No predictor_config specified")
        # TODO: How to model gordo spesific input and output vs our clean interface?
        timeseries_input_config = config.get("timeseries-api-input", {})
        timeseries_output_config = config.get("timeseries-api-output", {})
        # Augment config with some parameters
        config["data_provider"] = TimeSeriesDataProvider(**timeseries_input_config)
        config["prediction_forwarder"] = TimeSeriesPredictionForwarder(**timeseries_output_config)
        self.client = Client(**config)

    def execute_prediction(self, prediction_name: str, data: SensorData) -> PredictionData:
        """
        Train and/or run data through a given model
        """
        result = self.client.predict(data.time_range.from_time, data.time_range.to_time)
        pd = PredictionData(name=prediction_name, time_range=data.time_range, result=result)
        return pd
