from datetime import datetime
import time
import traceback
from os import environ
import typing
import logging
import pprint
from latigo.sensor_data import TimeRange, SensorData, PredictionData
from latigo.sensor_data.sensor_data import MockSensorDataProvider
from latigo.gordo import GordoPredictionExecutionProvider
from latigo.prediction_execution import MockPredictionExecutionProvider, DevNullPredictionExecutionProvider
from latigo.prediction_storage import DevNullPredictionStorageProvider
from latigo.task_queue import Task, DevNullTaskQueue
from latigo.task_queue.event_hub import EventHubTaskQueueDestionation


logger = logging.getLogger(__name__)


class PredictionExecutor:

    # Inflate task queue connection from config
    def _prepare_task_queue(self):
        self.task_queue_config = self.config.get("task_queue", None)
        if not self.task_queue_config:
            raise Exception("No task queue config specified")
        task_queue_type = self.task_queue_config.get("type", None)
        self.task_queue = None
        if "event_hub" == task_queue_type:
            self.task_queue = EventHubTaskQueueDestionation(self.task_queue_config)
        else:
            self.task_queue = DevNullTaskQueue(self.task_queue_config)
        self.idle_time = datetime.now()
        self.idle_number = 0
        if not self.task_queue:
            raise Exception("No task queue configured")

    # Inflate sensor data provider from config
    def _prepare_predictor(self):
        self.predictor_config = self.config.get("predictor", None)
        if not self.predictor_config:
            raise Exception("No predictor_config specified")
        predictor_type = self.predictor_config.get("type", None)
        self.name = self.predictor_config.get("name", "executor")
        self.predictor = None
        if "gordo" == predictor_type:
            self.predictor = GordoPredictionExecutionProvider(self.sensor_data, self.prediction_storage, self.predictor_config)
        elif "mock" == predictor_type:
            self.predictor = MockPredictionExecutionProvider(self.sensor_data, self.prediction_storage, self.predictor_config)
        else:
            self.predictor = DevNullPredictionExecutionProvider(self.sensor_data, self.prediction_storage, self.predictor_config)
        if not self.predictor:
            raise Exception("No predictor configured, cannot continue...")

    # Inflate prediction storage provider from config
    def _prepare_sensor_data(self):
        self.sensor_data_config = self.config.get("sensor_data", None)
        if not self.sensor_data_config:
            raise Exception("No sensor_data_config specified")
        sensor_data_type = self.sensor_data_config.get("type", None)
        self.sensor_data = None
        if "influx" == sensor_data_type:
            self.predictor = InfluxSensorDataProvider(self.sensor_data_config)
        else:
            self.predictor = DevNullSensorDataProvider(self.sensor_data_config)
        if not self.sensor_data:
            raise Exception("No sensor data configured, cannot continue...")

    # Inflate prediction provider from config
    def _prepare_prediction_storage(self):
        self.prediction_storage_config = self.config.get("prediction_storage", None)
        if not self.prediction_storage_config:
            raise Exception("No prediction_storage_config specified")
        prediction_storage_type = self.prediction_storage_config.get("type", None)
        self.prediction_storage = None
        if "influx" == prediction_storage_type:
            self.predictor = InfluxPredictionStorageProvider(self.prediction_storage_config)
        else:
            self.predictor = DevNullPredictionStorageProvider(self.prediction_storage_config)
        if not self.prediction_storage:
            raise Exception("No prediction storage configured, cannot continue...")

    def __init__(self, config: dict):
        if not config:
            raise Exception("No config specified")
        self.config = config
        # Make sure we have task queue
        self._prepare_task_queue()
        # Make sure we have input sensor data
        self._prepare_sensor_data()
        # Make sure we have output prediction storage
        self._prepare_prediction_storage()
        # Create the predictor
        self._prepare_predictor()

    def _fetch_task(self) -> typing.Optional[Task]:
        """
        The task describes what the executor is supposed to do. This internal helper fetches one task from event hub
        """
        task = None
        try:
            task = self.task_queue.get_task()
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
            self.sensor_data.get_data_for_range(time_range)
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
            logger.error(f"Could not execute prediction for task {task}: {e}")
            traceback.print_exc()
        return prediction_data

    def _store_prediction_data(self, task, prediction_data: PredictionData):
        """
        Prediction data represents the result of performing predictions on sensor data. This internal helper stores one bulk of prediction data to the store
        """
        try:
            self.prediction_storage.put_predictions(prediction_data)
        except Exception as e:
            logger.error(f"Could not store prediction data for task {task}: {e}")
            traceback.print_exc()

    def idle_count(self, has_task):
        if self.idle_number > 0:
            logger.info(f"Idle for {self.idle_number} cycles ({self.idle_time-datetime.now()})")
            self.idle_number = 0
            self.idle_time = datetime.now()
        else:
            self.idle_number += 1

    def run(self):
        if self.receiver:
            logger.info(f"Starting processing in {self.__class__.__name__}")
            done = False
            iteration_number = 0
            error_number = 0
            while not done:
                iteration_number += 1
                try:
                    task = self._fetch_task()
                    if task:
                        logger.info(f"Processing '{task}' for {self.__class__.__name__}")
                        sensor_data = self._fetch_sensor_data(task)
                        prediction_data = self._execute_prediction(task, sensor_data)
                        self._store_prediction_data(task, prediction_data)
                        self.idle_count(True)
                    else:
                        self.idle_count(False)
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
