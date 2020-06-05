import logging
import typing

import pylogctx
import sys
from gordo import __version__ as gordo_version
from gordo.client.io import BadGordoRequest, HttpUnprocessableEntity, NotFound, ResourceGone
from gordo.machine.dataset.base import InsufficientDataError
from gordo.machine.dataset.datasets import InsufficientDataAfterRowFilteringError
from requests_ms_auth import __version__ as auth_version

from latigo import __version__ as latigo_version
from latigo.auth import auth_check
from latigo.gordo import NoTagDataInDataLake
from latigo.log import measure
from latigo.metadata_storage import prediction_metadata_storage_provider_factory
from latigo.model_info import model_info_provider_factory
from latigo.prediction_execution import prediction_execution_provider_factory
from latigo.prediction_storage import prediction_storage_provider_factory
from latigo.sensor_data import sensor_data_provider_factory
from latigo.task_queue import task_queue_receiver_factory
from latigo.time_series_api import get_time_series_id_from_response
from latigo.time_series_api.misc import MODEL_INPUT_OPERATION
from latigo.time_series_api.time_series_exceptions import NoCommonAssetFound
from latigo.types import PredictionDataSet, Task

GORDO_EXCEPTIONS = (ResourceGone, NotFound, BadGordoRequest, HttpUnprocessableEntity)
IOC_DATA_EXCEPTIONS = (InsufficientDataAfterRowFilteringError, InsufficientDataError, NoTagDataInDataLake)

logger = logging.getLogger(__name__)


class PredictionExecutor:
    def __init__(self, config: dict):
        self._is_ready = True  # might be needed to exit execution-loop
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

    @measure("execute_prediction")
    def execute_prediction_for_task(self, task: Task, revision: str) -> typing.Optional[PredictionDataSet]:
        """Execute prediction for the given model and time range.

        Return: prediction data OR None (if error occurred).
        """
        model_training_period = self.model_info_provider.get_model_training_dates(
            project_name=task.project_name, model_name=task.model_name, revision=revision
        )

        return self.prediction_executor_provider.execute_prediction(
            task=task, revision=revision, model_training_period=model_training_period,
        )

    @measure("store_prediction_data_and_metadata")
    def store_prediction_data_and_metadata(self, prediction_data: PredictionDataSet):
        """Store prediction data (what represents the result of performing predictions on sensor data) and its metadata.

        1. Store just one bulk of prediction data. Do not send predictions for different models at ones.
        2. Store metadata of the prediction.
        """

        output_tag_names, output_time_series_ids = self.prediction_storage_provider.put_prediction(prediction_data)
        input_time_series_ids = self._get_tags_time_series_ids_for_model(prediction_data)

        self.prediction_metadata_storage_provider.put_prediction_metadata(
            prediction_data, output_tag_names, output_time_series_ids, input_time_series_ids
        )

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

        spec = self.model_info_provider.get_spec(
            project_name=prediction_data.meta_data.project_name,
            model_name=prediction_data.meta_data.model_name,
        )

        for tag in spec.tag_list:
            if tag.name in input_time_series_ids.keys():
                meta = self.prediction_storage_provider.get_meta_by_name(name=tag.name, asset_id=tag.asset)

                tag_id = get_time_series_id_from_response(meta)
                input_time_series_ids[tag.name] = tag_id

        missing_tags = {key: val for key, val in input_time_series_ids.items() if not val}
        if missing_tags:
            raise ValueError("[TAG_NOT_FOUND]: " + ";".join(missing_tags.keys()))
        return input_time_series_ids

    def run(self):
        """Execute models predictions one by one in the loop."""
        try:
            self._run()
        finally:
            self.task_queue.close()

    def _run(self):
        pylogctx.context.clear()

        while self._is_ready:
            try:
                self.process_one_prediction_task()
            except IOC_DATA_EXCEPTIONS as err:
                logger.warning("Data error: %r", err)
            except GORDO_EXCEPTIONS as err:
                logger.warning("Gordo error: %r", err)
            except NoCommonAssetFound as err:
                logger.warning("Prediction was not stored: %r", err)
            except Exception:
                logger.exception("Unknown error")
            except KeyboardInterrupt:
                self._is_ready = False
            finally:
                pylogctx.context.clear()

    @measure("process_prediction_task", logger=logger)
    def process_one_prediction_task(self):
        """Fetch and make prediction for one model from queue."""
        task = self.task_queue.get_task()
        if not task:
            logger.warning(f"[No task was received from queue] Will re-fetch.")
            return

        pylogctx.context.update(task=task)
        logger.info("Starting task processing.")

        revision = self.model_info_provider.get_project_latest_revisions(task.project_name)
        pylogctx.context.update(revision=revision)

        prediction_data = self.execute_prediction_for_task(task, revision)
        self.store_prediction_data_and_metadata(prediction_data)
