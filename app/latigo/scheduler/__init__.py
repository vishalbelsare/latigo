import sys
import logging
import pandas as pd
import datetime

import pylogctx

from pytz import utc
from requests import HTTPError

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
        self._is_ready = True  # might be needed to exit scheduling-loop
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
        self.run_at_once = self.scheduler_config.get("run_at_once", False)

    def print_summary(self):
        now = datetime.datetime.now(utc)
        next_start = f"{self.continuous_prediction_timer.closest_start_time(now=now)} " \
                     f"(in {human_delta(self.continuous_prediction_timer.time_left(now=now))})"
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

        model_names_by_project = self.model_info_provider.get_all_model_names_by_project(projects=projects)

        for project_name, models in model_names_by_project.items():
            for model_name in models:
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

    def run(self):
        """Start the main loop."""
        logger.info("Scheduler started processing")
        try:
            if self.run_at_once:
                self._run()

            while self._is_ready:
                try:
                    self.continuous_prediction_timer.wait_for_trigger()
                    self._run()
                except KeyboardInterrupt:
                    self._is_ready = False
                except HTTPError as err:
                    logger.exception("Error occurred in scheduler: HTTPError: %s", err.response.text)
                except Exception:
                    logger.exception("Error occurred in scheduler")
        finally:
            self.task_queue.close()

    def _run(self):
        start = datetime.datetime.now(utc)
        self.perform_prediction_step()
        interval = datetime.datetime.now(utc) - start
        logger.info(f"Scheduling took {human_delta(interval)}")
