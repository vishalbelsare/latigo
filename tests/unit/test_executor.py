import logging
from unittest.mock import MagicMock, patch, ANY

import pytest
from requests import HTTPError, Timeout, Response

from latigo.executor import GORDO_EXCEPTIONS, IOC_DATA_EXCEPTIONS, PredictionExecutor
from latigo.gordo import NoTagDataInDataLake
from latigo.time_series_api.time_series_exceptions import NoCommonAssetFound
from tests.factories.task import TaskFactory


@pytest.mark.parametrize("basic_executor", [True], indirect=["basic_executor"])
@patch("latigo.executor.PredictionExecutor.process_one_prediction_task", new=MagicMock(side_effect=Exception("error")))
@patch("latigo.executor.logging.Logger.error")
def test_run_exception(logger_error_mock, basic_executor: PredictionExecutor):
    basic_executor.run()
    logger_error_mock.assert_called_once_with("Unknown error", exc_info=True)


@patch("latigo.executor.logging.Logger.warning")
def test_process_one_prediction_task_no_task(logger_warn_mock, basic_executor):
    with patch.object(basic_executor.task_queue, "get_task", return_value=None):
        res = basic_executor.process_one_prediction_task()

    assert res is None
    logger_warn_mock.assert_called_once_with("[No task was received from queue] Will re-fetch.")


@patch("latigo.executor.PredictionExecutor.store_prediction_data_and_metadata", new=MagicMock())
@patch("latigo.executor.PredictionExecutor.execute_prediction_for_task", new=MagicMock())
def test_process_one_prediction_task_success(basic_executor):
    task = TaskFactory()
    with patch.object(basic_executor.task_queue, "get_task", return_value=task):
        basic_executor.process_one_prediction_task()


def test_execute_prediction_for_task_success(basic_executor):
    task = TaskFactory()
    revision = "000"

    client_mock = MagicMock(name="client_mock")
    client_mock.predict.return_value = [[ANY, ANY, []]]
    with patch.object(
        basic_executor.prediction_executor_provider.gordo_pool, "allocate_instance", return_value=client_mock
    ):
        basic_executor.execute_prediction_for_task(task=task, revision=revision)

        client_mock.predict.assert_called_once_with(
            start=task.from_time, end=task.to_time, targets=[task.model_name], revision=revision
        )


@pytest.mark.parametrize("exception", GORDO_EXCEPTIONS+IOC_DATA_EXCEPTIONS+(NoCommonAssetFound([]),))
@pytest.mark.parametrize("basic_executor", [True], indirect=["basic_executor"])
def test_execute_prediction_for_task_exception(exception, basic_executor: PredictionExecutor, caplog):
    task = TaskFactory()

    if exception in GORDO_EXCEPTIONS:
        error_message = "Gordo error"
    elif exception in IOC_DATA_EXCEPTIONS:
        error_message = "Data error"
    else:
        error_message = "Prediction was not stored"

    if exception == NoTagDataInDataLake:
        exception = exception(**task.__dict__, e=error_message)
    elif type(exception) is type:
        # If it's an exception class, initialise it
        exception = exception(error_message)

    with patch.object(basic_executor.prediction_executor_provider, "execute_prediction", side_effect=exception):
        basic_executor.run()
    assert ('latigo.executor', logging.WARNING, f"{ error_message }: { repr(exception) }") in caplog.record_tuples


@pytest.mark.parametrize("basic_executor", [True], indirect=["basic_executor"])
@pytest.mark.parametrize("exception", (HTTPError, Timeout))
def test_execute_prediction_for_unknown_errors(exception, basic_executor: PredictionExecutor, caplog):
    if exception == HTTPError:
        error_message = "Unknown error: HTTPError: response_text"
    else:
        error_message = "Unknown error"

    exception = exception(error_message)
    if type(exception) == HTTPError:
        exception.response = Response()
        exception.response._content = "response_text".encode()

    with patch.object(basic_executor.prediction_executor_provider, "execute_prediction", side_effect=exception):
        basic_executor.run()
    assert ('latigo.executor', logging.ERROR, error_message) in caplog.record_tuples
