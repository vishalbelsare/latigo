import logging
import pickle
import traceback
import typing
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class Task:
    name: str
    from_time: datetime = datetime.now() - timedelta(0, 20)
    to_time: datetime = datetime.now()

    def serialize(self) -> typing.Optional[bytes]:
        """
        Serialize a task to bytes
        """
        task_bytes = None
        try:
            task_bytes = pickle.dumps(self)
        except pickle.PicklingError as e:
            logger.error(f"Could not pickle task: {e}")
            traceback.print_exc()
        return task_bytes


def deserialize_task(task_bytes) -> typing.Optional[Task]:
    """
    Deserialize a task from bytes
    """
    task = None
    try:
        task = pickle.loads(task_bytes)
    except pickle.UnpicklingError as e:
        logger.error(f"Could not unpickle task of size {len(task_bytes)}bytes: {e}")
        traceback.print_exc()
    return task


class TaskQueueDestinationInterface:
    def put_task(self, task: Task):
        """
        Put one task on the queue
        """


class TaskQueueSourceInterface:
    def get_task(self) -> Task:
        """
        Return exactly one task from queue or block
        """


class DevNullTaskQueue(TaskQueueDestinationInterface, TaskQueueSourceInterface):
    def __init__(self, conf: dict):
        pass

    def get_task(self) -> Task:
        return Task("null")

    def put_task(self, task: Task):
        pass
