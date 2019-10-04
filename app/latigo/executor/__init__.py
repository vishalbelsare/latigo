# pylint: disable=C0413,C0411,C0412
from latigo.log import setup_logging

logger = setup_logging(__name__)

# pylint: disable=C0413,C0411,C0412
from datetime import datetime
import time
import traceback
from os import environ
import pickle
import typing
from latigo.sensor_data import Task, TimeRange, SensorData, PredictionData
from latigo.sensor_data.sensor_data import MockSensorDataProvider
from latigo.prediction import GordoPredictionExecutionProvider
from latigo.prediction_storage import DevNullPredictionStorageProvider
from latigo.event_hub.receive import EventReceiveClient, EventConsumerClient


class PredictionExecutor:
    def __init__(self, do_async=False):
        self.in_connection_string = environ.get("LATIGO_INTERNAL_EVENT_HUB", None)
        print(f"PRED EXEC CON STR: {self.in_connection_string}")
        if not self.in_connection_string:
            raise Exception("No connection string specified for internal event hub. Please set environment variable LATIGO_INTERNAL_EVENT_HUB to valid connection string")
        self.sensor_data_provider = MockSensorDataProvider()
        self.predictor = GordoPredictionExecutionProvider()
        self.out_storage = DevNullPredictionStorageProvider(True)
        self.debug = False
        if not self.sensor_data_provider:
            raise Exception("No sensor data provider configured, cannot continue...")
        if not self.out_storage:
            raise Exception("No prediction store configured, cannot continue...")
        if not self.predictor:
            raise Exception("No predictor configured, cannot continue...")
        self.receiver = None
        self.consumer = None
        if do_async:
            self.consumer = EventConsumerClient(self.in_connection_string, self.debug)
        else:
            self.receiver = EventReceiveClient(self.in_connection_string, self.debug)

    def _fetch_task(self) -> typing.Optional[Task]:
        """
        The task describes what the executor is supposed to do. This internal helper fetches one task from event hub
        """
        task = None
        try:
            task_bytes = self.receiver.recieve_event_with_backoff()
            # logger.info(f"RECEIVED DATA: {pformat(task_bytes)}")
            task = pickle.loads(task_bytes)
            # logger.info(f"RECEIVED TASK: {task}")
        except Exception as e:
            logger.error(f"Could not fetch task: {e}")
            traceback.print_exc()
        return task

    def _fetch_sensor_data(self, task: Task) -> typing.Optional[SensorData]:
        """
        Sensor data is input to prediction. This internal helper fetches one bulk of sensor data
        """
        sensor_data = None
        try:
            time_range = TimeRange(task.from_time, task.to_time)
            self.sensor_data_provider.get_data_for_range(time_range)
        except Exception as e:
            logger.error(f"Could not fetch sensor data for task {task}: {e}")
            traceback.print_exc()
        return sensor_data

    def _execute_prediction(self, task: Task, sensor_data: SensorData) -> typing.Optional[PredictionData]:
        """
        This internal helper executes prediction on one bulk of data
        """
        prediction_data = None
        try:
            prediction_data = self.predictor.execute_prediction("some_name", sensor_data)
        except Exception as e:
            logger.error(f"Could not fetch sensor data for task {task}: {e}")
            traceback.print_exc()
        return prediction_data

    def _store_prediction_data(self, task, prediction_data: PredictionData):
        """
        Prediction data represents the result of performing predictions on sensor data. This internal helper stores one bulk of prediction data to the store
        """
        try:
            self.out_storage.put_predictions(prediction_data)
        except Exception as e:
            logger.error(f"Could not store prediction data for task {task}: {e}")
            traceback.print_exc()

    def run(self):
        if self.receiver:
            logger.info(f"Starting processing in {self.__class__.__name__}")
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
                            logger.info(f"Idle for {idle_number} cycles ({idle_time-datetime.now()})")
                        logger.info(f"Processing '{task}' for {self.__class__.__name__}")
                        sensor_data = self._fetch_sensor_data(task)
                        prediction_data = self._execute_prediction(task, sensor_data)
                        self._store_prediction_data(task, prediction_data)
                        idle_time = datetime.now()
                    else:
                        idle_number += 1
                        time.sleep(1)
                except Exception as e:
                    error_number += 1
                    logger.error("-----------------------------------")
                    logger.error(f"Error occurred in scheduler: {e}")
                    traceback.print_exc()
                    logger.error("")
                    time.sleep(1)
            logger.info(f"Stopping processing in {self.__class__.__name__}")
        else:
            logger.info(f"Skipping processing in {self.__class__.__name__}")

    def run_async(self):
        if self.consumer:
            logger.info(f"Starting async processing in {self.__class__.__name__}")
            done = False
            while not done:
                try:

                    def handle(data):
                        if data:
                            logger(f"Processing '{data}' for {self.__class__.__name__}")
                            data = f"Async Event '{data}'"
                            pd = PredictionData
                            pd.data = data
                            self.out_storage.put_predictions(pd)

                    self.consumer.consume_events(handle)
                except KeyboardInterrupt:
                    done = True
            logger.info(f"Stopping async processing in {self.__class__.__name__}")
        else:
            logger.info(f"Skipping async processing in {self.__class__.__name__}")
