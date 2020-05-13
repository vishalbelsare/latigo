from unittest.mock import MagicMock, patch

from latigo.executor import PredictionExecutor
from latigo.gordo import GordoModelInfoProvider
from tests.factories.task import TaskFactory


@patch("latigo.gordo.prediction_execution_provider.GordoClientPool", new=MagicMock())
@patch(
    "latigo.executor.model_info_provider_factory", new=MagicMock(side_effect=MagicMock(spec_set=GordoModelInfoProvider))
)
@patch("latigo.executor.PredictionExecutor._perform_auth_checks", new=MagicMock())
def test__execute_prediction_success(config):
    executor = PredictionExecutor(config=config)
    task = TaskFactory()
    revision = "000"

    client_mock = MagicMock(name="client_mock")
    with patch.object(executor.prediction_executor_provider.gordo_pool, "allocate_instance", return_value=client_mock):
        executor._execute_prediction(task=task, revision=revision)

        client_mock.predict.assert_called_once_with(
            start=task.from_time, end=task.to_time, targets=[task.model_name], revision=revision
        )
