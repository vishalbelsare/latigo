import logging
from datetime import datetime
import time
import traceback
from os import environ
#from latigo.utils import *
#from latigo.event_hub import *
from latigo.sensor_data import Task, TimeRange, SensorData, PredictionData
from latigo.sensor_data.sensor_data import MockSensorDataProvider
from latigo.prediction import GordoPredictionExecutionProvider
from latigo.prediction_storage import DevNullPredictionStorageProvider
from latigo.event_hub.receive import EventReceiveClient
import pickle
from pprint import pformat


"""
event_hub_connection_string = os.environ.get('LATIGO_EXECUTOR_EVENT_HUB', "fdkjgkfdjgkfdgjkfdg")
storage=MockPredictionStorageProvider()

executor=PredictionExecutor(event_hub_connection_string, storage)

executor.run()
"""


class PredictionExecutor:

    def __init__(self):
        self.logger = logging.getLogger(__class__.__name__)

        self.in_connection_string = environ.get(
            'LATIGO_INTERNAL_EVENT_HUB', None)
        if not self.in_connection_string:
            raise Exception(
                "No connection string specified for internal event hub. Please set environment variable LATIGO_INTERNAL_EVENT_HUB to valid connection string")
        self.sensor_data_provider = MockSensorDataProvider()
        self.predictor = GordoPredictionExecutionProvider()
        self.out_storage = DevNullPredictionStorageProvider(True)
        self.debug = False
        if not self.sensor_data_provider:
            raise Exception(
                "No sensor data provider configured, cannot continue...")
        if not self.out_storage:
            raise Exception(
                "No prediction store configured, cannot continue...")
        if not self.predictor:
            raise Exception("No predictor configured, cannot continue...")
        self.receiver = EventReceiveClient(
            self.in_connection_string, self.debug)
        #self.consumer=EventConsumerClient(in_connection_string, in_partition, in_consumer_group, in_offset, debug)

    def _fetch_task(self) -> Task:
        """
        The task describes what the executor is supposed to do. This internal helper fetches one task from event hub
        """
        task = None
        try:
            task_bytes = self.receiver.recieve_event()
            #self.logger.info(f"RECEIVED DATA: {pformat(task_bytes)}")
            task = pickle.loads(task_bytes)
            #self.logger.info(f"RECEIVED TASK: {task}")
        except Exception as e:
            self.logger.error("Could not fetch task")
            traceback.print_exc()
        return task

    def _fetch_sensor_data(self, task: Task) -> SensorData:
        """
        Sensor data is input to prediction. This internal helper fetches one bulk of sensor data
        """
        sensor_data = None
        try:
            time_range = TimeRange(task.from_time, task.to_time)
            self.sensor_data_provider.get_data_for_range(time_range)
        except Exception as e:
            self.logger.error(f"Could not fetch sensor data for task {task}")
            traceback.print_exc()
        return sensor_data

    def _execute_prediction(
            self,
            task: Task,
            sensor_data: SensorData) -> PredictionData:
        """
        This internal helper executes prediction on one bulk of data
        """
        prediction_data = None
        try:
            prediction_data = self.predictor.execute_prediction(
                'some_name', sensor_data)
        except Exception as e:
            self.logger.error(f"Could not fetch sensor data for task {task}")
            traceback.print_exc()
        return prediction_data

    def _store_prediction_data(task, prediction_data: PredictionData):
        """
        Prediction data represents the result of performing predictions on sensor data. This internal helper stores one bulk of prediction data to the store
        """
        try:
            self.out_storage.put_predictions(prediction_data)
        except Exception as e:
            self.logger.error(
                f"Could not store prediction data for task {task}")
            traceback.print_exc()
        return sensor_data

    def run(self):
        self.logger.info(f"Starting processing in {self.__class__.__name__}")
        done = False
        iteration_number = 0
        idle_time = datetime.now()
        idle_number = 0
        error_number = 0
        while not done:
            iteration_number += 1
            try:
                task = self._fetch_task()
                if task:
                    if idle_number > 0:
                        idle_number = 0
                        self.logger.info(
                            f"Idle for {idle_number} cycles ({idle_time-datetime.now()})")
                    self.logger.info(
                        f"Processing '{task}' for {self.__class__.__name__}")
                    sensor_data = self._fetch_sensor_data(task)
                    prediction_data = self._execute_prediction(
                        task, sensor_data)
                    self._store_prediction_data(task, prediction_data)
                    idle_time = datetime.now()
                else:
                    idle_number += 1
                    time.sleep(1)
            except Exception as e:
                error_number += 1
                self.logger.error("-----------------------------------")
                self.logger.error(f"Error occurred in scheduler: {e}")
                traceback.print_exc()
                self.logger.error("")
                time.sleep(1)
        self.logger.info(f"Stopping processing in {self.__class__.__name__}")

    def run_async(self):
        self.logger.info(
            f"Starting async processing in {self.__class__.__name__}")
        done = False
        while not done:
            try:
                def handle(data):
                    if data:
                        self.logger(
                            f"Processing '{data}' for {self.__class__.__name__}")
                        data = f"Async Event '{data}'"
                        pd = PredictionData
                        pd.data = data
                        self.out_storage.put_predictions(pd)
                self.consumer.consume_events(handle)
            except KeyboardInterrupt:
                done = True
        self.logger.info(
            f"Stopping async processing in {self.__class__.__name__}")
