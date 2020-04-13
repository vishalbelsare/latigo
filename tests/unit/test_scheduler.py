from datetime import datetime, timedelta

import pytest
from mock import MagicMock, patch

from latigo.model_info import Model
from latigo.scheduler import Scheduler
from tests.conftest import SCHEDULER_PREDICTION_DELAY, SCHEDULER_PREDICTION_INTERVAL

DATETIME_UTC_NOW = datetime.fromisoformat("2020-04-10T10:00:00.000000+00:00")
MODELS = [Model(model_name="model", project_name="project", tag_list=[], target_tag_list=[])]


@pytest.fixture
@patch("latigo.task_queue.kafka.Producer", new=MagicMock())
@patch("latigo.scheduler.Scheduler._prepare_model_info", new=MagicMock())
@patch("latigo.scheduler.Scheduler._perform_auth_checks", new=MagicMock())
def scheduler(schedule_config, monkeypatch) -> Scheduler:
    monkeypatch.setattr("latigo.scheduler.get_datetime_now_in_utc", MagicMock(return_value=DATETIME_UTC_NOW))
    scheduler = Scheduler(schedule_config)
    scheduler.models = MODELS
    return scheduler


def test_perform_prediction_step_put_task(scheduler: Scheduler):
    """Validates task serialisation and using UTC time."""
    with patch.object(scheduler.task_queue, "send_event") as send_event_mock:
        scheduler.perform_prediction_step()

        from_datetime = DATETIME_UTC_NOW + timedelta(days=-SCHEDULER_PREDICTION_DELAY)
        from_time = from_datetime.timestamp()
        to_time = (from_datetime + timedelta(minutes=+SCHEDULER_PREDICTION_INTERVAL)).timestamp()
        dumped_task = '{{"project_name": "project", "model_name": "model", ' '"from_time": {}, "to_time": {}}}'.format(
            from_time, to_time
        )

        send_event_mock.assert_called_once_with(dumped_task)
