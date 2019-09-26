from datetime import datetime
import typing
from typing import List, Set, Dict, Tuple, Optional

from latigo.sensor_data import *
from gordo_components.data_provider.base import GordoBaseDataProvider, capture_args
from cachetools import cached, TTLCache
import numpy as np
import pandas as pd

from gordo_components.client.forwarders import PredictionForwarder
from gordo_components.client import Client
from gordo_components.dataset.sensor_tag import SensorTag

class PredictionInfo:
    pass


class PredictionInformationProviderInterface:

    def get_prediction_info(prediction_name:str):
        """
        return any information about a named prediction
        """
        pass

    def get_predictions(filter:dict):
        """
        return a list of predictions matching the given filter.
        """
        pass

class MockPredictionInformationProvider(PredictionInformationProviderInterface):

    def get_prediction_info(prediction_name:str) -> PredictionInfo:
        """
        return any information about a named prediction
        """
        pi=PredictionInfo()
        pi.name=prediction_name
        return pi

    def get_predictions(filter:dict) -> List[PredictionInfo]:
        """
        return a list of predictions matching the given filter.
        """
        list=[]
        for i in range(3):
            pi=PredictionInfo()
            pi.name=f"pred_{i}"
            list.append(pi)
        return list



class PredictionExecutionProviderInterface:

    def execute_prediction (prediction_name:str, data:SensorData) -> PredictionData:
        """
        Train and/or run data through a given model
        """
        pass




class MockPredictionExecutionProvider(PredictionExecutionProviderInterface):

    def execute_prediction (prediction_name:str, data:SensorData) -> PredictionData:
        """
        Train and/or run data through a given model
        """
        pd=PredictionData
        pd.name=prediction_name
        pd.data=data
        return pd


class TimeSeriesPredictionForwarder(PredictionForwarder):
    """
    To be used as a 'forwarder' for the gordo prediction client
    After instantiation, it is a coroutine which accepts prediction dataframes
    which it will pass onto time series api via event hub
    """

    def __init__(
        self,
        connection_string: str,
        partition: Optional[str] = "0",
        debug: bool = False,
        n_retries=5,
    ):
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
        parts = parse_event_hub_connection_string(connection_string)




class TimeSeriesDataProvider(GordoBaseDataProvider):
    """
    Get a GordoBaseDataset which returns unstructed values for X and y. Each instance
    uses the same seed, so should be a function (same input -> same output)
    """

    @capture_args
    def __init__(
        self,
        connection_string: str,
        partition: str,
        prefetch: int,
        consumer_group: str,
        offset: str,
        debug: bool,
        n_retries: int,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.connection_string=connection_string
        self.partition=partition
        self.prefetch=prefetch
        self.consumer_group=consumer_group
        self.offset=offset
        self.debug=debug

    def can_handle_tag(self, tag: SensorTag):
        return True

    def load_series(
        self,
        from_ts: datetime,
        to_ts: datetime,
        tag_list: typing.List[SensorTag],
        dry_run: typing.Optional[bool] = False,
    ) -> typing.Iterable[pd.Series]:
        if dry_run:
            raise NotImplementedError(
                "Dry run for TimeSeriesDataProvider is not implemented"
            )
        self.receiver=EventReceiveClient(self.connection_string, self.partition, self.consumer_group, self.prefetch, self.offset, self.debug)
        for tag in tag_list:
            nr = random.randint(self.min_size, self.max_size)

            random_index = self._random_dates(from_ts, to_ts, n=nr)
            series = pd.Series(
                index=random_index,
                name=tag.name,
                data=np.random.random(size=len(random_index)),
            )
        yield series

class GordoPredictionExecutionProvider(PredictionExecutionProviderInterface):
    def execute_prediction (prediction_name:str, data:SensorData) -> PredictionData:
        """
        Train and/or run data through a given model
        """

        config=utils.load_yaml('config.yaml')
        pprint.pprint(config)
        client_config=config.get('gordo-client', {})
        timeseries_input_config=config.get('timeseries-api-input', {})
        timeseries_output_config=config.get('timeseries-api-output', {})
        # Augment config with some parameters
        client_config['data_provider']= TimeSeriesDataProvider(**timeseries_input_config)
        client_config['prediction_forwarder']= TimeSeriesPredictionForwarder(**timeseries_output_config)
        client=Client(**client_config)
        result = client.predict(data.from_time, data.to_time)
        pd=PredictionData
        pd.name=prediction_name
        pd.data=data
        return pd

