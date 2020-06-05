import sys
import logging
import pandas as pd
import datetime

import pylogctx
from time import sleep

from pytz import utc

from latigo import __version__ as latigo_version
from gordo import __version__ as gordo_version
from requests_ms_auth import __version__ as auth_version
from latigo.model_metadata_info import model_metadata_info_factory
from latigo.types import Task
from latigo.task_queue import task_queue_sender_factory
from latigo.model_info import model_info_provider_factory
from latigo.clock import OnTheClockTimer
from latigo.utils import human_delta
from latigo.auth import auth_check

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(self, config: dict):
        if not config:
            self._fail("No config specified")
        self.config = config
        self._prepare_task_queue()
        self._prepare_model_info()
        self._prepare_models_metadata_info_provider()
        self._perform_auth_checks()
        self._prepare_scheduler()

    def _fail(self, message: str):
        logger.error(message)
        raise sys.exit(message)

    # Inflate model info connection from config
    def _prepare_model_info(self):
        self.model_info_config = self.config.get("model_info", None)
        if not self.model_info_config:
            self._fail("No model info config specified")
        self.model_info_provider = model_info_provider_factory(self.model_info_config)
        if not self.model_info_provider:
            self._fail("No model info configured")

    # Inflate task queue connection from config
    def _prepare_task_queue(self):
        self.task_queue_config = self.config.get("task_queue", None)
        if not self.task_queue_config:
            self._fail("No task queue config specified")
        self.task_queue = task_queue_sender_factory(self.task_queue_config)
        self.idle_time = datetime.datetime.now()
        self.idle_number = 0
        if not self.task_queue:
            self._fail("No task queue configured")

    def _prepare_models_metadata_info_provider(self):
        """Initialize provider for fetching models metadata."""
        self.models_metadata_info_config = self.config.get("models_metadata_info", None)
        if not self.models_metadata_info_config:
            self._fail("No models_metadata_info specified")
        self.models_metadata_info_provider = model_metadata_info_factory(
            self.models_metadata_info_config
        )
        if not self.models_metadata_info_provider:
            self._fail(f"No prediction metadata storage configured, cannot continue...")

    # Perform a basic authentication test up front to fail early with clear error output
    def _perform_auth_checks(self):
        auth_configs = [self.model_info_config.get("auth"), self.models_metadata_info_config.get("auth")]
        res, msg, auth_session = auth_check(auth_configs)
        if not res:
            self._fail(f"{msg} for session:\n'{auth_session}'")
        else:
            logger.info(
                f"Auth test succeedded for all {len(auth_configs)} configurations."
            )

    # Inflate scheduler from config
    def _prepare_scheduler(self):
        self.scheduler_config = self.config.get("scheduler", None)
        if not self.scheduler_config:
            self._fail("No scheduler config specified")
        self.name = self.scheduler_config.get("name", "unnamed_scheduler")
        try:
            cpst = self.scheduler_config.get(
                "continuous_prediction_start_time", "08:00"
            )
            self.continuous_prediction_start_time = datetime.datetime.strptime(
                cpst, "%H:%M"
            ).time()
        except Exception as e:
            self._fail(
                f"Could not parse '{cpst}' into continuous_prediction_start_time: {e}"
            )
        try:
            cpsc = self.scheduler_config.get("continuous_prediction_interval", "30m")
            self.continuous_prediction_interval = pd.to_timedelta(cpsc)
        except Exception as e:
            self._fail(
                f"Could not parse '{cpsc}' into continuous_prediction_interval: {e}"
            )
        try:
            cpd = self.scheduler_config.get("continuous_prediction_delay", "3h")
            self.continuous_prediction_delay = pd.to_timedelta(cpd)
        except Exception as e:
            self._fail(f"Could not parse '{cpd}' into continuous_prediction_delay: {e}")
        self.continuous_prediction_timer = OnTheClockTimer(
            start_time=self.continuous_prediction_start_time,
            interval=self.continuous_prediction_interval,
        )
        self.run_at_once = self.scheduler_config.get("run_at_once", True)

    def print_summary(self):
        next_start = f"{self.continuous_prediction_timer.closest_start_time()} (in {human_delta(self.continuous_prediction_timer.time_left())})"
        logger.info(
            f"\nScheduler settings:\n"
            f"  Latigo Version:   {latigo_version}\n"
            f"  Gordo Version:    {gordo_version}\n"
            f"  Auth Version:     {auth_version}\n"
            f"  Run at once :     {self.run_at_once}\n"
            f"  Start time :      {self.continuous_prediction_start_time}\n"
            f"  Interval:         {human_delta(self.continuous_prediction_interval)}\n"
            f"  Data delay:       {human_delta(self.continuous_prediction_delay)}\n"
            f"  Next start:       {next_start}\n"
        )

    def perform_prediction_step(self):
        stats_projects_ok = set()
        stats_models_ok = set()

        stats_start_time_utc = datetime.datetime.now(utc)

        # Use UTC time cause Queue will ignore timezone.
        # Also Gordo client ignores microseconds, so round them to 0
        prediction_start_time_utc = stats_start_time_utc.replace(microsecond=0) - self.continuous_prediction_delay
        prediction_end_time_utc = prediction_start_time_utc.replace(microsecond=0) + self.continuous_prediction_interval

        # fetch projects from the API
        projects = self.models_metadata_info_provider.get_projects()
        if not projects:
            raise ValueError("No projects were fetch for scheduling the predictions.")

        models = self.model_info_provider.get_all_models(projects=projects)

        for model in models:
            project_name = model.project_name
            if not project_name:
                logger.error("No project name found for model, skipping model")
                continue

            model_name = model.model_name
            if not model_name:
                logger.error("No model name found for model in project: %s", project_name)
                continue

            task = Task(
                project_name=project_name,
                model_name=model_name,
                from_time=prediction_start_time_utc,
                to_time=prediction_end_time_utc,
            )
            with pylogctx.context(task=task):
                self.task_queue.put_task(task)

                stats_projects_ok.add(project_name)
                stats_models_ok.add(model_name)

        logger.info(
            f"Scheduled {len(stats_models_ok)} models over {len(stats_projects_ok)} projects."
        )

    def on_time(self):
        try:
            start = datetime.datetime.now()
            self.perform_prediction_step()
            interval = datetime.datetime.now() - start
            logger.info(f"Scheduling took {human_delta(interval)}")
            if interval < datetime.timedelta(seconds=1):
                sleep(interval.total_seconds())
        except KeyboardInterrupt:
            logger.info("Keyboard abort triggered, shutting down")
            return True
        except Exception:
            logger.exception("Error occurred in scheduler")

        return False

    def run(self):
        logger.info("Scheduler started processing")
        done = False
        start = datetime.datetime.now()
        if self.run_at_once:
            done = self.on_time()

        while not done:
            logger.info(
                "Next prediction will occur at %s (in %s)",
                self.continuous_prediction_timer.closest_start_time(),
                human_delta(self.continuous_prediction_timer.time_left())
            )
            if self.continuous_prediction_timer.wait_for_trigger(now=start):
                done = self.on_time()
