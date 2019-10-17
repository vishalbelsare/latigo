import traceback
import pickle
import time
import logging
import pandas as pd
from datetime import timedelta
from os import environ
import typing
from latigo.event_hub.send import EventSenderClient
from latigo.sensor_data import Task
from latigo.utils import Timer

logger = logging.getLogger(__name__)


class Scheduler:
    def _prepare_task_queue(self):
        self.task_config = self.config.get("task_queue", None)
        if not self.task_config:
            raise Exception("No task config specified")
        self.sender = EventSenderClient(self.task_config)

    def _prepare_scheduler(self):
        self.scheduler_config = self.config.get("scheduler", None)
        if not self.scheduler_config:
            raise Exception("No scheduler config specified")
        self.name = self.scheduler_config.get("name", "unnamed_scheduler")
        self.configuration_sync_interval = pd.to_timedelta(self.scheduler_config.get("configuration_sync_interval", "1m"))
        self.continuous_prediction_interval = pd.to_timedelta(self.scheduler_config.get("continuous_prediction_interval", "30m"))
        selfdback_fill_max_interval = pd.to_timedelta(self.scheduler_config.get("back_fill_max_interval", "1d"))
        self.configuration_sync_timer = Timer(self.configuration_sync_interval)
        self.continuous_prediction_timer = Timer(self.continuous_prediction_interval)

    def __init__(self, config: dict):
        if not config:
            raise Exception("No config specified")
        self.config = config
        self._prepare_scheduler()
        self._prepare_task_queue()
        self.task_serial = 0

    def _serialize_task(self, task: Task) -> typing.Optional[bytes]:
        """
        Serialize a task to bytes
        """
        task_bytes = None
        try:
            task_bytes = pickle.dumps(task)
        except pickle.PicklingError as e:
            logger.error(f"Could not pickle task: {e}")
            traceback.print_exc()
        return task_bytes

    def synchronize_configuration(self):
        logger.info(f"Synchronizing configuration")

    def perform_prediction_step(self):
        logger.info(f"Performing prediction step")
        for _ in range(10):
            task = Task(f"Task {self.task_serial} from {self.name}")
            # logger.info(f"SENDING TASK: {task}")
            # logger.info(f"Generating '{task}' for {self.__class__.__name__}")
            task_bytes = self._serialize_task(task)
            # logger.info(f"SENDING DATA: {pformat(task_bytes)}")
            if task_bytes:
                try:
                    self.sender.send_event(task_bytes)
                    self.task_serial += 1
                except Exception as e:
                    logger.error(f"Could not send task: {e}")
                    traceback.print_exc()

    def run(self):
        logger.info(f"Starting {self.__class__.__name__}")
        logger.info(f"Configuration sync: {self.configuration_sync_timer}")
        logger.info(f"Prediction step: {self.continuous_prediction_timer}")
        done = False
        while not done:
            try:
                if self.configuration_sync_timer.is_triggered():
                    # Restart timer
                    self.configuration_sync_timer.start()
                    # Do the configuratio sync
                    self.synchronize_configuration()

                if self.continuous_prediction_timer.is_triggered():
                    # Restart timer
                    self.continuous_prediction_timer.start()
                    # Do the prediction task queueing
                    self.perform_prediction_step()

                time.sleep(1)

            except KeyboardInterrupt:
                logger.info("Keyboard abort triggered, shutting down")
                done = True
            except Exception as e:
                logger.error("-----------------------------------")
                logger.error(f"Error occurred in scheduler: {e}")
                traceback.print_exc()
                logger.error("")
        logger.info(f"Stopping {self.__class__.__name__}")
