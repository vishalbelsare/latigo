import logging
import time
import traceback
from os import environ
from latigo.event_hub import *
from latigo.sensor_data import *
from latigo.utils import *
from latigo.prediction import *
from latigo.prediction_storage import *



"""
event_hub_connection_string = os.environ.get('LATIGO_EXECUTOR_EVENT_HUB', "fdkjgkfdjgkfdgjkfdg")
storage=MockPredictionStorageProvider()

executor=PredictionExecutor(event_hub_connection_string, storage)

executor.run()
"""
class PredictionExecutor:

    def __init__(self, ):
        self.logger = logging.getLogger(__class__.__name__)

        self.in_connection_string = environ.get('LATIGO_INTERNAL_EVENT_HUB', None)
        if not self.in_connection_string:
            raise Exception("No connection string specified for internal event hub. Please set environment variable LATIGO_INTERNAL_EVENT_HUB to valid connection string")
        self.in_partition="0"
        self.in_consumer_group ="$default"
        self.in_prefetch = 5000
        self.in_offset:str = "-1"
        self.out_partition = "0"
        self.out_storage = DevNullPredictionStorageProvider(True)
        self.debug = False
        if not self.out_storage:
            raise Exception("No prediction store configured, cannot continue...")
        self.receiver=EventReceiveClient(self.in_connection_string, self.in_partition, self.in_consumer_group, self.in_prefetch, self.in_offset, self.debug)
        #self.consumer=EventConsumerClient(in_connection_string, in_partition, in_consumer_group, in_offset, debug)

    def run(self):
        self.logger.info(f"Starting processing in {self.__class__.__name__}")
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
                else:
                    time.sleep(1)
            except KeyboardInterrupt:
                done=True
            except Exception as e:
                self.logger.error("-----------------------------------")
                self.logger.error(f"Error occurred in scheduler: {e}")
                traceback.print_exc()
                self.logger.error("")
        self.logger.info(f"Stopping processing in {self.__class__.__name__}")

    def run_async(self):
        self.logger.info(f"Starting async processing in {self.__class__.__name__}")
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
        self.logger.info(f"Stopping async processing in {self.__class__.__name__}")
