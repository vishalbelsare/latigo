from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, call, ANY

import pytest

from latigo.gordo import GordoModelInfoProvider, Task
from latigo.model_info import Model
from latigo.scheduler import Scheduler
from tests.conftest import SCHEDULER_PREDICTION_DELAY, SCHEDULER_PREDICTION_INTERVAL
from tests.factories.models import ModelFactory

DATETIME_UTC_NOW = datetime.fromisoformat("2020-04-10T10:00:00.000000+00:00")
MODELS = [Model(model_name="model", project_name="project", tag_list=[], target_tag_list=[])]
PROJECTS_FROM_API = ["ioc-1000", "ioc-1099"]


@pytest.fixture
@patch("latigo.metadata_api.client.MetadataAPIClient._create_session", new=MagicMock())
@patch("latigo.task_queue.kafka.Producer", new=MagicMock())
@patch("latigo.scheduler.Scheduler._perform_auth_checks", new=MagicMock())
def scheduler(schedule_config) -> Scheduler:
    scheduler = Scheduler(schedule_config)
    scheduler.model_info_provider = Mock(spec=GordoModelInfoProvider)
    scheduler.model_info_provider.get_all_models.return_value = MODELS
    return scheduler


@pytest.mark.parametrize("microsecond", [0, 987654, 1])
@patch("latigo.metadata_api.client.MetadataAPIClient.get_projects", new=MagicMock(return_value=PROJECTS_FROM_API))
def test_perform_prediction_step_put_task(scheduler, microsecond):
    """Validates task serialisation and using UTC time."""
    with patch("latigo.scheduler.datetime") as mock_dt, patch.object(scheduler, "task_queue") as task_queue:
        mock_dt.datetime.now.return_value = DATETIME_UTC_NOW.replace(microsecond=microsecond)
        scheduler.perform_prediction_step()

    from_time = DATETIME_UTC_NOW + timedelta(days=-SCHEDULER_PREDICTION_DELAY)
    to_time = from_time + timedelta(minutes=+SCHEDULER_PREDICTION_INTERVAL)

    task_queue.assert_has_calls(
        [call.put_task(Task(project_name="project", model_name="model", from_time=from_time, to_time=to_time))]
    )


def test_run(scheduler):
    with patch.object(scheduler, "task_queue") as task_queue, patch.object(
        scheduler, "models_metadata_info_provider"
    ) as md_client:
        # Ensure the loop is interrupted after the first task is placed
        task_queue.put_task.side_effect = KeyboardInterrupt

        md_client.get_projects.return_value = ["project1"]
        scheduler.run()

    task_queue.assert_has_calls(
        [call.put_task(Task(project_name="project", model_name=ANY, from_time=ANY, to_time=ANY)), call.close()]
    )


@pytest.mark.parametrize("models", [[ModelFactory(), ModelFactory(), ModelFactory()], [ModelFactory()]])
@patch("latigo.metadata_api.client.MetadataAPIClient.get_projects", new=MagicMock(return_value=PROJECTS_FROM_API))
def test_perform_prediction_step_multiple_projects(models, scheduler):
    with patch.object(scheduler.task_queue, "put_task") as mock_put_task, patch.object(
        scheduler.model_info_provider, "get_all_models", new=Mock(return_value=models)
    ), patch("latigo.scheduler.datetime") as mock_dt:
        mock_dt.datetime.now.return_value = DATETIME_UTC_NOW
        scheduler.perform_prediction_step()

    from_datetime = DATETIME_UTC_NOW + timedelta(days=-SCHEDULER_PREDICTION_DELAY)
    to_time = from_datetime + timedelta(minutes=+SCHEDULER_PREDICTION_INTERVAL)

    expected_calls = []
    for model in models:
        expected_calls.append(
            call(
                Task(
                    project_name=model.project_name,
                    model_name=model.model_name,
                    from_time=from_datetime,
                    to_time=to_time,
                )
            )
        )

    mock_put_task.assert_has_calls(expected_calls)
