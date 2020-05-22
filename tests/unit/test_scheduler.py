import json
from datetime import datetime, timedelta

import pytest
from mock import MagicMock, patch, Mock

from latigo.gordo import GordoModelInfoProvider
from latigo.model_info import Model
from latigo.scheduler import Scheduler
from tests.conftest import SCHEDULER_PREDICTION_DELAY, SCHEDULER_PREDICTION_INTERVAL

DATETIME_UTC_NOW = datetime.fromisoformat("2020-04-10T10:00:00.000000+00:00")
MODELS = [Model(model_name="model", project_name="project", tag_list=[], target_tag_list=[])]


@pytest.fixture
@patch("latigo.task_queue.kafka.Producer", new=MagicMock())
@patch("latigo.scheduler.Scheduler._prepare_model_info", new=MagicMock())
@patch("latigo.scheduler.Scheduler._perform_auth_checks", new=MagicMock())
def scheduler(schedule_config) -> Scheduler:
    scheduler = Scheduler(schedule_config)
    scheduler.model_info_provider = Mock(spec=GordoModelInfoProvider)
    scheduler.model_info_provider.get_all_models.return_value = MODELS
    return scheduler


@pytest.mark.parametrize("microsecond", [0, 987654, 1])
def test_perform_prediction_step_put_task(scheduler, microsecond):
    """Validates task serialisation and using UTC time."""
    with patch("latigo.scheduler.datetime") as mock_dt, patch.object(scheduler.task_queue, "send_event") as send_event:
        mock_dt.datetime.now.return_value = DATETIME_UTC_NOW.replace(microsecond=microsecond)
        scheduler.perform_prediction_step()

    from_datetime = DATETIME_UTC_NOW + timedelta(days=-SCHEDULER_PREDICTION_DELAY)
    from_time = from_datetime.timestamp()
    to_time = (from_datetime + timedelta(minutes=+SCHEDULER_PREDICTION_INTERVAL)).timestamp()
    dumped_task = json.dumps(
        {"project_name": "project", "model_name": "model", "from_time": from_time, "to_time": to_time}
    )

    send_event.assert_called_once_with(dumped_task)
