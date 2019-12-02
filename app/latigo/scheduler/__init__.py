import traceback
import time
import logging
import pprint
import typing
import pandas as pd
from datetime import datetime, timedelta
from os import environ
from latigo.types import Task
from latigo.task_queue import task_queue_sender_factory

from latigo.utils import Timer, human_delta
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
        self.model_filter["projects"] = []
        if "gordo" == model_info_type:
            self.model_info = GordoModelInfoProvider(self.model_info_config)
            self.model_filter["projects"] = self.model_info_config.get("projects", [])
            logger.info("FILTER:")
            logger.info(self.model_filter["projects"])
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
        self.task_queue = task_queue_sender_factory(self.task_queue_config)
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
        self.configuration_sync_timer = Timer(trigger_interval=self.configuration_sync_interval)
        self.continuous_prediction_timer = Timer(trigger_interval=self.continuous_prediction_interval)
        logger.info(f"Using configuration sync interval: {self.configuration_sync_interval}")
        logger.info(f"Using prediction interval:         {self.continuous_prediction_interval}")

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
        self.models = self.model_info.get_models(self.model_filter)
        logger.info(f"Found {len(self.models)} models")
        # logger.info(pprint.pformat(self.models))

    def perform_prediction_step(self):
        stats_projects_ok = {}
        stats_models_ok = {}
        stats_projects_bad = {}
        stats_models_bad = {}
        # TODO: Use clock once it is finished
        stats_start_time = datetime.now()
        prediction_start_time = datetime.now()
        prediction_end_time = prediction_start_time + self.continuous_prediction_interval
        early_termination = False
        for model in self.models:
            project_name = model.get("project", None)
            if not project_name:
                logger.error("No project name found, skipping model")
                continue
            model_name = model.get("name", None)
            if not model_name:
                logger.error("No model name found, skipping model")
                continue
            task = Task(project_name=project_name, model_name=model_name, from_time=prediction_start_time, to_time=prediction_end_time)
            try:
                self.task_queue.put_task(task)
                self.task_serial += 1
                # logger.info(f"Enqueued '{model_name}' in '{project_name}'")
                stats_projects_ok[project_name] = stats_projects_ok.get(project_name, 0) + 1
                stats_models_ok[model_name] = stats_models_ok.get(model_name, 0) + 1
            except Exception as e:
                # logger.error(f"Could not send task: {e}")
                # traceback.print_exc()
                stats_projects_bad[project_name] = stats_projects_bad.get(project_name, "") + f", {e}"
                stats_models_bad[model_name] = stats_models_bad.get(model_name, "") + f", {e}"
                raise e
            if early_termination:
                logger.warning("Early termination for testing is in place")
                break
        stats_interval = datetime.now() - stats_start_time
        logger.info(f"Scheduled {len(stats_models_ok)} models in {len(stats_projects_ok)} projects in {human_delta(stats_interval)}")
        if len(stats_models_bad) > 0 or len(stats_projects_bad) > 0:
            logger.error(f"          {len(stats_models_bad)} models in {len(stats_projects_bad)} projects failed")
            for name in stats_models_bad:
                logger.error(f"          + {name}({stats_models_bad[name]})")

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
                logger.error("-----------------------------------")
        logger.info(f"Stopping {self.__class__.__name__}")
