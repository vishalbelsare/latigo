import traceback
import time
import logging
import pprint
import typing
import pandas as pd
from datetime import datetime, timedelta
from os import environ
from latigo.task_queue import Task, DevNullTaskQueue
from latigo.task_queue.event_hub import EventHubTaskQueueDestionation
from latigo.utils import Timer
from latigo.gordo import GordoModelInfoProvider

logger = logging.getLogger(__name__)


class Scheduler:

    # Inflate model info connection from config
    def _prepare_model_info(self):
        self.model_info_config = self.config.get("model_info", None)
        if not self.model_info_config:
            raise Exception("No model info config specified")
        model_info_type = self.model_info_config.get("type", None)
        self.model_info = None
        self.model_filter = {}
        if "gordo" == model_info_type:
            self.model_info = GordoModelInfoProvider(self.model_info_config)
            self.model_filter["project"] = self.model_info_config.get("project", [])
        else:
            self.model_info = DevNullModelInfo(self.model_info_config)
        self.idle_time = datetime.now()
        self.idle_number = 0
        if not self.model_info:
            raise Exception("No model info configured")

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

    # Inflate scheduler from config
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
        self._prepare_task_queue()
        self._prepare_model_info()
        self._prepare_scheduler()
        self.task_serial = 0
        self.models: typing.List[typing.Dict] = []

    def synchronize_configuration(self):
        logger.info(f"Synchronizing configuration")
        self.models = self.model_info.get_models(self.model_filter)
        logger.info("-GOT MODELS-")
        logger.info(pprint.pformat(self.models))

    def perform_prediction_step(self):
        logger.info(f"Performing prediction step")
        for model in self.models:
            task = Task(f"Task {self.task_serial} from {self.name} for {model}")
            try:
                self.task_queue.put_task(task)
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
