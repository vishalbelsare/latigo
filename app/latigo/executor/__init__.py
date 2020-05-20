import datetime
import logging
import sys
import typing

from gordo import __version__ as gordo_version
from gordo.client.io import BadGordoRequest, HttpUnprocessableEntity, NotFound, ResourceGone
from gordo.machine.dataset.base import InsufficientDataError
from gordo.machine.dataset.datasets import InsufficientDataAfterRowFilteringError
from requests import HTTPError
from requests_ms_auth import __version__ as auth_version

from latigo import __version__ as latigo_version
from latigo.auth import auth_check
from latigo.gordo import NoTagDataInDataLake
from latigo.metadata_storage import prediction_metadata_storage_provider_factory
from latigo.model_info import model_info_provider_factory
from latigo.prediction_execution import prediction_execution_provider_factory
from latigo.prediction_storage import prediction_storage_provider_factory
from latigo.sensor_data import sensor_data_provider_factory
from latigo.task_queue import task_queue_receiver_factory
from latigo.time_series_api import get_time_series_id_from_response
from latigo.time_series_api.misc import MODEL_INPUT_OPERATION
from latigo.time_series_api.time_series_exceptions import NoCommonAssetFound
from latigo.types import PredictionDataSet, SensorDataSpec, Task
from latigo.utils import human_delta

GORDO_EXCEPTIONS = (ResourceGone, NotFound, BadGordoRequest, HttpUnprocessableEntity)
GORDO_ERROR_IDENTIFIER = "Gordo error"
IOC_DATA_EXCEPTIONS = (InsufficientDataAfterRowFilteringError, InsufficientDataError, NoTagDataInDataLake)
IOC_ERROR_IDENTIFIER = "Data error"
TASK_LOG_VISUAL_SEPARATOR = "\n\n"

logger = logging.getLogger(__name__)


class PredictionExecutor:
    def __init__(self, config: dict):
        self._is_ready = True  # might be needed to exit execution-loop
        self.task_fetch_start = None
        self.config = config
        self._prepare_task_queue()
        self._prepare_sensor_data_provider()
        self._prepare_prediction_storage_provider()
        self._prepare_prediction_metadata_storage_provider()
        self._prepare_model_info()
        self._prepare_prediction_executor_provider()
        self._prepare_executor()
        self._perform_auth_checks()

    @staticmethod
    def _fail(message: str):
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
        self.task_queue = task_queue_receiver_factory(self.task_queue_config)
        self.idle_time = datetime.datetime.now()
        self.idle_number = 0
        if not self.task_queue:
            self._fail("No task queue configured")

    # Inflate sensor data provider from config
    def _prepare_sensor_data_provider(self):
        self.sensor_data_provider_config = self.config.get("sensor_data", None)
        if not self.sensor_data_provider_config:
            self._fail("No sensor_data_config specified")
        self.sensor_data_provider = sensor_data_provider_factory(self.sensor_data_provider_config)
        if not self.sensor_data_provider:
            self._fail(f"No sensor data configured, cannot continue...")

    # Inflate prediction storage provider from config
    def _prepare_prediction_storage_provider(self):
        self.prediction_storage_provider_config = self.config.get("prediction_storage", None)
        if not self.prediction_storage_provider_config:
            self._fail("No prediction_storage_config specified")
        self.prediction_storage_provider = prediction_storage_provider_factory(self.prediction_storage_provider_config)
        if not self.prediction_storage_provider:
            self._fail(f"No prediction storage configured, cannot continue...")

    # Inflate prediction metadata storage provider from config
    def _prepare_prediction_metadata_storage_provider(self):
        """Initialize provider for storing of prediction metadata."""
        prediction_metadata_storage_provider_config = self.config.get("prediction_metadata_storage", None)
        if not prediction_metadata_storage_provider_config:
            self._fail("No prediction_metadata_storage specified")
        self.prediction_metadata_storage_provider = prediction_metadata_storage_provider_factory(
            prediction_metadata_storage_provider_config
        )
        if not self.prediction_metadata_storage_provider:
            self._fail(f"No prediction metadata storage configured, cannot continue...")

    # Inflate prediction executor provider from config
    def _prepare_prediction_executor_provider(self):
        self.prediction_executor_provider_config = self.config.get("predictor", None)
        if not self.prediction_executor_provider_config:
            self._fail("No prediction_executor_provider_config specified")
        self.prediction_executor_provider = prediction_execution_provider_factory(
            self.sensor_data_provider, self.prediction_storage_provider, self.prediction_executor_provider_config,
        )
        self.name = self.prediction_executor_provider_config.get("name", "executor")
        if not self.prediction_executor_provider:
            self._fail(f"No prediction_executor_provider configured, cannot continue...")

    # Perform a basic authentication test up front to fail early with clear error output
    def _perform_auth_checks(self):
        auth_configs = [self.model_info_config.get("auth")]
        res, msg, auth_session = auth_check(auth_configs)
        if not res:
            self._fail(f"{msg} for session:\n'{auth_session}'")
        else:
            logger.info(f"Auth test succeedded for all {len(auth_configs)} configurations.")

    # Inflate executor from config
    def _prepare_executor(self):
        self.executor_config = self.config.get("executor", {})
        if not self.executor_config:
            self._fail("No executor config specified")

        self.log_debug_enabled = self.executor_config.get("log_debug_enabled", False)

    @staticmethod
    def print_summary():
        """Log some debug info about executor."""
        logger.info(
            f"\nExecutor settings:\n"
            f"  Latigo Version:   {latigo_version}\n"
            f"  Gordo Version:    {gordo_version}\n"
            f"  Auth Version:     {auth_version}\n"
        )

    def fetch_spec(self, project_name: str, model_name: str) -> SensorDataSpec:
        return self.model_info_provider.get_spec(project_name=project_name, model_name=model_name)

    def _fetch_task(self) -> typing.Optional[Task]:
        """Fetch one task from event hub.

        The task describes what the executor is supposed to do.
        """
        return self.task_queue.get_task()

    def execute_prediction_for_task(self, task: Task, revision: str) -> typing.Optional[PredictionDataSet]:
        """Execute prediction for the given model and time range.

        Return: prediction data OR None (if error occurred).
        """
        model_training_period = self.model_info_provider.get_model_training_dates(
            project_name=task.project_name, model_name=task.model_name, revision=revision
        )

        try:
            prediction_data = self.prediction_executor_provider.execute_prediction(
                task=task, revision=revision, model_training_period=model_training_period,
            )
        except IOC_DATA_EXCEPTIONS as e:
            logger.warning(self.format_error_message(IOC_ERROR_IDENTIFIER, e=e, task=task))
            return
        except GORDO_EXCEPTIONS as e:
            logger.warning(self.format_error_message(GORDO_ERROR_IDENTIFIER, e=e, task=task))
            return

        return prediction_data

    def store_prediction_data_and_metadata(self, task: Task, prediction_data: PredictionDataSet):
        """Store prediction data (what represents the result of performing predictions on sensor data) and its metadata.

        1. Store just one bulk of prediction data. Do not send predictions for different models at ones.
        2. Store metadata of the prediction.
        """
        # store predictions
        try:
            output_tag_names, output_time_series_ids = self.prediction_storage_provider.put_prediction(prediction_data)
            self._log_task_execution_time(label="stored to TS API")
        except NoCommonAssetFound as e:
            logger.error(self.format_error_message("Prediction was not stored", e=e, task=task))
            return

        # store predictions metadata
        input_time_series_ids = self._get_tags_time_series_ids_for_model(prediction_data)
        try:
            self.prediction_metadata_storage_provider.put_prediction_metadata(
                prediction_data, output_tag_names, output_time_series_ids, input_time_series_ids
            )
            self._log_task_execution_time(label="stored to Metadata API")
        except HTTPError as e:
            logger.error(self.format_error_message("Metadata was not stored", e=e, task=task))
            return

    def _get_tags_time_series_ids_for_model(self, prediction_data: PredictionDataSet) -> typing.Dict[str, str]:
        """Fetch 'Time Series IDs' to the relevant 'input_tags'.

        Args:
            prediction_data: dataframe as a result of prediction execution and prediction metadata.
        """
        input_time_series_ids: typing.Dict[str, str] = {}  # {(operation, tag_name): time_series_id}.
        df_columns = prediction_data.data[0][1].columns

        # save tag names for further fetching its Time Series IDs
        for col in df_columns:
            operation = col[0]  # example: "start", "end", "model-input"
            tag_name = col[1]  # example: "1903.R-29TT3018.MA_Y"

            if operation == MODEL_INPUT_OPERATION:
                # save tag names for further fetching its Time Series IDs
                input_time_series_ids[tag_name] = ""

        spec = self.fetch_spec(prediction_data.meta_data.project_name, prediction_data.meta_data.model_name)

        for tag in spec.tag_list:
            if tag.name in input_time_series_ids.keys():
                meta, error = self.prediction_storage_provider._get_meta_by_name(name=tag.name, asset_id=tag.asset)
                if error:
                    # Raise error if tag does not exist
                    raise ValueError(f"Tag was not found. Name='{tag.name}' asset='{tag.asset}': error='{error}'")

                tag_id = get_time_series_id_from_response(meta)
                input_time_series_ids[tag.name] = tag_id

        missing_tags = {key: val for key, val in input_time_series_ids.items() if not val}
        if missing_tags:
            raise ValueError("[TAG_NOT_FOUND]: " + ";".join(missing_tags.keys()))
        return input_time_series_ids

    def run(self):
        """Execute models predictions on by one in the loop."""
        while self._is_ready:
            try:
                self.process_one_prediction_task()
            except Exception as e:
                logger.error(self.format_error_message("[Unknown error]", e=e), stack_info=True)

    def process_one_prediction_task(self):
        """Fetch and make prediction for one model from queue."""
        self.task_fetch_start = datetime.datetime.now()
        task = self._fetch_task()
        if not task:
            logger.warning(f"[No task was received from queue] Will re-fetch.")
            return

        self._log_task_execution_time(label="Prediction_task_info", task=task, force_log_writing=True)

        revision = self.model_info_provider.get_project_latest_revisions(task.project_name)

        prediction_data = self.execute_prediction_for_task(task, revision)
        if prediction_data is None:
            return
        self._log_task_execution_time(label="Got the predictions")

        self.store_prediction_data_and_metadata(task, prediction_data)
        self._log_task_execution_time(
            label="Total task execution time", task=task, force_log_writing=True, add_new_line=True
        )

    @staticmethod
    def make_prediction_task_info(task: Task) -> str:
        """Make info about prediction task for logging."""
        return f"'{task.project_name}.{task.model_name}', prediction: from '{task.from_time}' to '{task.to_time}'"

    def _log_task_execution_time(
        self, label: str, task: Task = None, force_log_writing: bool = False, add_new_line: bool = False
    ):
        """Log time from the beginning of the task execution.

        Args:
            - label: identifier for logs for future search;
            - task: task to be additionally logged;
            - force_log_writing: if True log will be written despite "self.log_debug_enabled";
            - add_new_line: add `task_visual_separator` to the end of log.

        Note: 'self.task_fetch_start' should be initialized previously.
        """
        if not self.log_debug_enabled and not force_log_writing:
            return

        logger.info(
            f"[TIMEIT: {label}] {human_delta(datetime.datetime.now() - self.task_fetch_start)}."
            f"{self.make_prediction_task_info(task) if task else ''}"
            f"{TASK_LOG_VISUAL_SEPARATOR if add_new_line else ''}"
        )

    @classmethod
    def format_error_message(cls, label: str, e: Exception, task: Task = None) -> str:
        """Format error message for log."""
        return (
            f"[{label}] [{type(e).__name__}] "
            f"{f'Model: {cls.make_prediction_task_info(task)}' if task else ''}. Error: '{e}'."
        )
