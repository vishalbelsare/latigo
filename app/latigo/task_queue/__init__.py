import logging
import pickle
import json
import traceback
import typing
from dataclasses import dataclass
from datetime import datetime, timedelta
from latigo.types import Task

logger = logging.getLogger(__name__)


def serialize_task(task, mode="json") -> typing.Optional[bytes]:
    """
    Serialize a task to bytes
    """
    task_bytes = None
    if mode == "pickle":
        try:
            task_bytes = pickle.dumps(task)
        except pickle.PicklingError as e:
            logger.error(f"Could not serialize task to json pickle: {e}")
            traceback.print_exc()
    else:
        try:
            # Rely on dataclass_json
            task_bytes = task.to_json()
        except Exception as e:
            logger.error(f"Could not serialize task to json: {e}")
            traceback.print_exc()
    return task_bytes


def deserialize_task(task_bytes, mode="json") -> typing.Optional[Task]:
    """
    Deserialize a task from bytes
    """
    task = None
    if mode == "pickle":
        try:
            task = pickle.loads(task_bytes)
        except pickle.UnpicklingError as e:
            logger.error(f"Could not deserialize task from pickle of size {len(task_bytes)}bytes: {e}")
            traceback.print_exc()
    else:
        try:
            # Rely on dataclass_json
            task = Task.from_json(task_bytes)
        except Exception as e:
            logger.error(f"Could not deserialize task from json of size {len(task_bytes)}bytes: {e}")
            traceback.print_exc()
    return task


class TaskQueueSenderInterface:
    def put_task(self, task: Task):
        """
        Put one task on the queue
        """


class TaskQueueReceiverInterface:
    def get_task(self) -> Task:
        """
        Return exactly one task from queue or block
        """


class DevNullTaskQueue(TaskQueueSenderInterface, TaskQueueReceiverInterface):
    def __init__(self, conf: dict):
        pass

    def get_task(self) -> Task:
        return Task("null")

    def put_task(self, task: Task):
        pass


def task_queue_receiver_factory(task_queue_config):
    task_queue_type = task_queue_config.get("type", None)
    task_queue = None
    if "event_hub" == task_queue_type:
        from latigo.task_queue.event_hub import EventHubTaskQueueReceiver

        task_queue = EventHubTaskQueueReceiver(task_queue_config)
    elif "kafka" == task_queue_type:
        from latigo.task_queue.kafka import KafkaTaskQueueReceiver

        task_queue = KafkaTaskQueueReceiver(task_queue_config)
    else:
        task_queue = DevNullTaskQueue(task_queue_config)
    return task_queue


def task_queue_sender_factory(task_queue_config):
    task_queue_type = task_queue_config.get("type", None)
    task_queue = None
    if "event_hub" == task_queue_type:
        from latigo.task_queue.event_hub import EventHubTaskQueueSender

        task_queue = EventHubTaskQueueSender(task_queue_config)
    elif "kafka" == task_queue_type:
        from latigo.task_queue.kafka import KafkaTaskQueueSender

        task_queue = KafkaTaskQueueSender(task_queue_config)
    else:
        task_queue = DevNullTaskQueue(task_queue_config)
    return task_queue
