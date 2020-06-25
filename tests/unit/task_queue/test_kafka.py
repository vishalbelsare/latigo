"""Test for the Kafka producers and consumers."""
from unittest.mock import patch, sentinel, Mock, ANY

import pytest

from latigo.task_queue.kafka import KafkaTaskQueueSender
from latigo.types import Task


@pytest.fixture
def sender():
    """Provide KafkaTaskQueueSender with mocked Producer."""
    with patch("latigo.task_queue.kafka.Producer"), patch(
        "latigo.task_queue.kafka.prepare_kafka_config", return_value=(sentinel.config, sentinel.topic, None)
    ):
        return KafkaTaskQueueSender({"connection_string": "mock"})


def test_put_task(sender):
    task = Mock(spec=Task)

    sender.put_task(task)
    sender.producer.produce.assert_called_once_with(sentinel.topic, task.to_json.return_value, on_delivery=ANY)
    sender.producer.poll.assert_called_once_with(0)


def test_close(sender):
    sender.close()
    sender.producer.flush.assert_called_once_with()


def test_close_already_closed(sender):
    sender.producer.close.side_effect = RuntimeError

    sender.close()
    sender.producer.flush.assert_called_once_with()
