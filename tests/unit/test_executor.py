from unittest.mock import ANY, MagicMock, patch

import pytest

from latigo.executor import (
    GORDO_ERROR_IDENTIFIER,
    GORDO_EXCEPTIONS,
    IOC_DATA_EXCEPTIONS,
    IOC_ERROR_IDENTIFIER,
    PredictionExecutor,
)
from latigo.gordo import NoTagDataInDataLake
from latigo.metadata_api.metadata_exceptions import MetadataStoringError
from latigo.time_series_api.time_series_exceptions import NoCommonAssetFound
from tests.factories.task import TaskFactory


@pytest.mark.parametrize("basic_executor", [True], indirect=["basic_executor"])
@patch("latigo.executor.PredictionExecutor.process_one_prediction_task", new=MagicMock(side_effect=Exception("error")))
@patch("latigo.executor.logging.Logger.error")
def test_run_exception(logger_error_mock, basic_executor: PredictionExecutor):
    basic_executor.run()
    logger_error_mock.assert_called_once_with("[[Unknown error]] [Exception] . Error: 'error'.", stack_info=True)


@patch("latigo.executor.logging.Logger.warning")
def test_process_one_prediction_task_no_task(logger_warn_mock, basic_executor):
    basic_executor._fetch_task = MagicMock(return_value=None)
    res = basic_executor.process_one_prediction_task()

    assert res is None
    logger_warn_mock.assert_called_once_with("[No task was received from queue] Will re-fetch.")


@patch("latigo.executor.PredictionExecutor.store_prediction_data_and_metadata")
@patch("latigo.executor.PredictionExecutor.execute_prediction_for_task", new=MagicMock(return_value=None))
def test_process_one_prediction_task_no_prediction_data(store_prediction_data_and_metadata, basic_executor):
    task = TaskFactory()
    basic_executor._fetch_task = MagicMock(return_value=task)

    res = basic_executor.process_one_prediction_task()
    assert res is None
    store_prediction_data_and_metadata.assert_not_called()


@patch("latigo.executor.PredictionExecutor.store_prediction_data_and_metadata", new=MagicMock())
@patch("latigo.executor.PredictionExecutor.execute_prediction_for_task", new=MagicMock())
def test_process_one_prediction_task_success(basic_executor):
    task = TaskFactory()
    basic_executor._fetch_task = MagicMock(return_value=task)

    res = basic_executor.process_one_prediction_task()
    assert res is None


def test_execute_prediction_for_task_success(basic_executor):
    task = TaskFactory()
    revision = "000"

    client_mock = MagicMock(name="client_mock")
    with patch.object(
        basic_executor.prediction_executor_provider.gordo_pool, "allocate_instance", return_value=client_mock
    ):
        basic_executor.execute_prediction_for_task(task=task, revision=revision)

        client_mock.predict.assert_called_once_with(
            start=task.from_time, end=task.to_time, targets=[task.model_name], revision=revision
        )


@pytest.mark.parametrize("exception", [ex for ex in GORDO_EXCEPTIONS + IOC_DATA_EXCEPTIONS])
@patch("latigo.executor.logging.Logger.warning")
def test_execute_prediction_for_task_exception(logger_warn, exception, basic_executor):
    task = TaskFactory()

    error_message = GORDO_ERROR_IDENTIFIER if exception in GORDO_EXCEPTIONS else IOC_ERROR_IDENTIFIER
    if exception == NoTagDataInDataLake:
        exception = exception(**task.__dict__, e=error_message)
    else:
        exception = exception(error_message)

    with patch.object(basic_executor.prediction_executor_provider, "execute_prediction", side_effect=exception):
        basic_executor.execute_prediction_for_task(task=task, revision=ANY)

        logger_warn.assert_called_once_with(basic_executor.format_error_message(error_message, e=exception, task=task))


@patch("latigo.executor.PredictionExecutor._get_tags_time_series_ids_for_model", new=MagicMock())
@patch("latigo.executor.logging.Logger.error")
def test_store_prediction_data_and_metadata_no_common_asset(logger_error, basic_executor):
    task = TaskFactory()

    exception = NoCommonAssetFound([])
    with patch.object(basic_executor.prediction_storage_provider, "put_prediction", side_effect=exception):
        basic_executor.store_prediction_data_and_metadata(task=task, prediction_data=ANY)

        logger_error.assert_called_once_with(
            basic_executor.format_error_message("Prediction was not stored", e=exception, task=task)
        )


@patch("latigo.executor.PredictionExecutor._get_tags_time_series_ids_for_model", new=MagicMock())
@patch("latigo.executor.logging.Logger.error")
def test_store_prediction_data_and_metadata_metadata_error(logger_error, basic_executor):
    task = TaskFactory()

    exception = MetadataStoringError("Metadata Error")
    with patch.object(
        basic_executor.prediction_metadata_storage_provider, "put_prediction_metadata", side_effect=exception
    ):
        basic_executor.store_prediction_data_and_metadata(task=task, prediction_data=ANY)

        logger_error.assert_called_once_with(
            basic_executor.format_error_message("Metadata was not stored", e=exception, task=task)
        )
