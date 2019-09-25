import logging
import time
import traceback
from events import EventReceiveClient
from sensor_data import *
from utils import *


class PredictionExecutor:

    def __init__(self, in_connection_string:str, out_storage:PredictionStorageProviderInterface, in_partition:str="0", out_partition:str="0", in_prefetch:int=5000, in_consumer_group:str="$default", in_offset:str="-1", debug:bool=False):
        self.logger = logging.getLogger(__class__.__name__)
        self.receiver=EventReceiveClient(in_connection_string, in_partition, in_consumer_group, in_prefetch, in_offset, debug)
        #self.consumer=EventConsumerClient(in_connection_string, in_partition, in_consumer_group, in_offset, debug)
        self.out_storage=out_storage

    def run(self):
        self.logger.info(f"Starting {self.__class__.__name__}")
        done=False
        while not done:
            try:
                data=self.receiver.recieve_event()
                if data:
                    self.logger.info(f"Processing '{data}' for {self.__class__.__name__}")
                    data=f"Event '{data}'"
                    pd=PredictionData
                    pd.data=data
                    self.out_storage.put_predictions(pd)
                time.sleep(1000)
            except KeyboardInterrupt:
                done=True
            except Exception as e:
                self.logger.error("-----------------------------------")
                self.logger.error(f"Error occurred in scheduler: {e}")
                traceback.print_exc()
                self.logger.error("")
        self.logger.info(f"Stopping {self.__class__.__name__}")

    def run_async(self):
        self.logger.info(f"Starting async execution for {self.__class__.__name__}")
        done=False
        while not done:
            try:
                def handle(data):
                    if data:
                        self.logger(f"Processing '{data}' for {self.__class__.__name__}")
                        data=f"Event '{data}'"
                        pd=PredictionData
                        pd.data=data
                        self.out_storage.put_predictions(pd)
                self.consumer.consume_events(handle)
            except KeyboardInterrupt:
                done=True
        self.logger.info(f"Stop async {self.__class__.__name__}")
