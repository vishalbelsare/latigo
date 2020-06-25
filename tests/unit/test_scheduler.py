from datetime import datetime, timedelta, date as datetime_date
from unittest.mock import Mock, patch, MagicMock, call, ANY

import pytest

from latigo.gordo import Task
from latigo.scheduler import Scheduler
from tests.conftest import SCHEDULER_PREDICTION_DELAY, SCHEDULER_PREDICTION_INTERVAL

DATETIME_UTC_NOW = datetime.fromisoformat("2020-04-10T10:00:00.000000+00:00")
PROJECTS_FROM_API = ["ioc-1000", "ioc-1099"]


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


@pytest.mark.parametrize("scheduler", ([True], ), indirect=["scheduler"])
@patch("latigo.scheduler.OnTheClockTimer.wait_for_trigger", new=MagicMock())
def test_run(scheduler: Scheduler):
    with patch.object(scheduler, "task_queue") as task_queue, patch.object(
        scheduler, "models_metadata_info_provider"
    ) as md_client:
        md_client.get_projects.return_value = ["project1"]
        scheduler.run()

    task_queue.assert_has_calls(
        [call.put_task(Task(project_name="project", model_name=ANY, from_time=ANY, to_time=ANY))]
    )


@pytest.mark.parametrize("models_by_project", [
    {"project_1": ["model_1", "model_2"]},
    {"project_1": ["model_1"], "project_2": ["model_2"]}
])
@patch("latigo.metadata_api.client.MetadataAPIClient.get_projects", new=MagicMock(return_value=PROJECTS_FROM_API))
def test_perform_prediction_step_multiple_projects(models_by_project, scheduler):
    with patch.object(scheduler.task_queue, "put_task") as mock_put_task, patch.object(
        scheduler.model_info_provider, "get_all_model_names_by_project", new=Mock(return_value=models_by_project)
    ), patch("latigo.scheduler.datetime") as mock_dt:
        mock_dt.datetime.now.return_value = DATETIME_UTC_NOW
        scheduler.perform_prediction_step()

    from_datetime = DATETIME_UTC_NOW + timedelta(days=-SCHEDULER_PREDICTION_DELAY)
    to_time = from_datetime + timedelta(minutes=+SCHEDULER_PREDICTION_INTERVAL)

    expected_calls = []
    for project_name, models in models_by_project.items():
        for model_name in models:
            expected_calls.append(
                call(
                    Task(
                        project_name=project_name,
                        model_name=model_name,
                        from_time=from_datetime,
                        to_time=to_time,
                    )
                )
            )

    mock_put_task.assert_has_calls(expected_calls)


@pytest.mark.parametrize("scheduler", [(True, True, True, True)], indirect=["scheduler"])
@patch("latigo.clock.sleep")
def test_run_intervals_sleep(clock_sleep_mock, scheduler: Scheduler):
    """Test scheduling behavior of the Clock.

    If interval is 5 minutes between scheduling predictions, logic is:
        10:01:00 - scheduler was run -> "sleep" for 4 mins;
        10:05:00 - first prediction scheduling made;
        10:10:00 - each next scheduling should be made in 5 mins;
        ...
    """
    times_now = ["10:01:00", "10:05:20", "10:10:25", "10:16:13"]
    expected_sleeps = [240.0, 280.0, 275.0, 227.0]

    datetime_now = [datetime.fromisoformat(f"2020-04-10T{t}.000000+00:00") for t in times_now]
    with patch("latigo.clock.datetime") as mock_clock_dt, patch.object(scheduler, "_run", new=Mock()):
        mock_clock_dt.datetime.now.side_effect = datetime_now
        mock_clock_dt.date.side_effect = datetime_date
        mock_clock_dt.datetime.combine.side_effect = datetime.combine
        scheduler.run()
    clock_sleep_mock.assert_has_calls([call(secs) for secs in expected_sleeps])
