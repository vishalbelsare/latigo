import json
import logging
import pprint
import typing
from time import sleep

from confluent_kafka import Producer, Consumer, KafkaException, KafkaError

from latigo.task_queue import (
    deserialize_task,
    serialize_task,
    TaskQueueSenderInterface,
    TaskQueueReceiverInterface,
)
from latigo.types import Task
from latigo.utils import parse_event_hub_connection_string

logger = logging.getLogger(__name__)
logger_confluent = logging.getLogger(__name__ + ".confluent")


def stats_callback(stats_json_str):
    stats_json = json.loads(stats_json_str)
    logger.info("\nKAFKA Stats: {}\n".format(pprint.pformat(stats_json)))


def prepare_kafka_config(
    config: typing.Dict[str, typing.Any]
) -> typing.Tuple[typing.Optional[dict], str, typing.Optional[str]]:
    connection_string = str(config.get("connection_string"))
    if not connection_string:
        return None, "", "No connection_string in kafka configuration"
    parts = parse_event_hub_connection_string(connection_string) or {}
    if not parts:
        return (
            None,
            "",
            f"No parts found in kafka connection_string '{connection_string}'",
        )
    topic = parts["entity_path"] or ""
    # fmt: off
    return {
        "bootstrap.servers": f"{parts.get('endpoint')}:9093",
        "security.protocol": config.get("security.protocol"),
        "ssl.ca.location": config.get("ssl.ca.location"),
        "sasl.mechanism": config.get("sasl.mechanism"),
        "sasl.username": "$ConnectionString",
        "sasl.password": config.get("connection_string"),
        "client.id": config.get("client.id"),
        "group.id": config.get("group.id"),
        "request.timeout.ms": config.get("request.timeout.ms"),
        "session.timeout.ms": config.get("session.timeout.ms"),
        "enable.auto.commit": config.get("enable.auto.commit"),
        "auto.commit.interval.ms": config.get("auto.commit.interval.ms"),
        "max.poll.interval.ms": config.get("max.poll.interval.ms"),
        "default.topic.config": config.get("default.topic.config"),
        "debug": config.get("debug"),
        "logger": logger_confluent,
        }, topic, None
    # fmt: on


class KafkaTaskQueueSender(TaskQueueSenderInterface):
    def __init__(self, config: dict):
        # Producer configuration
        # See https://github.com/edenhill/librdkafka/blob/master/CONFIGURATION.md
        # See https://github.com/edenhill/librdkafka/wiki/Using-SSL-with-librdkafka#prerequisites for SSL issues
        self.poll_timeout_sec = config.get("poll_timeout_sec", 100)
        self.config, self.topic, err = prepare_kafka_config(config)
        if not self.config:
            raise Exception(f"No config parsed: {err}")
        if not self.topic:
            raise Exception("No topic configured: {err}")

        # Create Producer instance
        self.producer = Producer(self.config)
        logger.info(f"Producer will send messages to the topic - '{config['connection_string'].split('=')[-1]}'.")

        # Wait until all messages have been delivered
        logger.info(f"Waiting for {len(self.producer)} deliveries")
        self.producer.flush()

    def __del__(self):
        if self.producer:
            self.producer.close()

    def send_event(self, msg: typing.Optional[bytes]):
        try:
            self.producer.produce(self.topic, msg, on_delivery=self.delivery_callback)
        except BufferError as e:
            logger.info(
                f"Local producer queue is full ({len(self.producer)} messages awaiting delivery): try again. {e}"
            )
        # self.producer.poll(0)

    def put_task(self, task: Task):
        task_bytes: typing.Optional[bytes] = None
        try:
            task_bytes = serialize_task(task)
        except Exception as e:
            logger.error(f"Error while serizlising task: {e}")
            logger.error(f" + Task: {task}")
            raise e
        if not task_bytes:
            raise Exception("Could not serialize task")
        self.send_event(task_bytes)

    @staticmethod
    def delivery_callback(err, msg):
        """This is called only when self.producer.poll(0) will be called.

        To test it: call self.producer.poll(0) from 'send_event' func.
        """
        if err:
            logger.error(f"Message failed delivery: {err} ({msg.topic()} [{msg.partition()}] @ {msg.offset()})")
        else:
            logger.info(f"Message delivered to {msg.topic()} [{msg.partition()}] @ {msg.offset()}")


class KafkaTaskQueueReceiver(TaskQueueReceiverInterface):
    def __init__(self, config: dict):
        # Consumer configuration
        # See https://github.com/edenhill/librdkafka/blob/master/CONFIGURATION.md
        self.poll_timeout_sec = config.get("poll_timeout_sec", 100)
        self.config, self.topic, err = prepare_kafka_config(config)
        if not self.config:
            raise Exception(f"No config parsed: {err}")
        if not self.topic:
            raise Exception("No topic configured: {err}")
        # Create Consumer instance
        self.consumer = Consumer(self.config)
        # Subscribe to topics
        self.subscribe_to_topic()

    def __del__(self):
        if self.consumer:
            self.consumer.close()

    def subscribe_to_topic(self):
        """Make a call to subscribe to the topic and do not wait for the response.

        Notes:
            "on_assign" is called when partition will be assigned or another consumer is already subscribed;
            "on_revoke" is called when re-balancing is made or subscription was revoked.
        """
        logger.info(
            f"[Subscribing] to the topic '{self.topic}'. Results of the subscription will be available through "
            f"the callback functions after 'poll()' func will be called."
        )
        self.consumer.subscribe([self.topic], on_assign=self.on_assignment_callback, on_revoke=self.on_revoke_callback)

    @staticmethod
    def on_assignment_callback(consumer, partitions: typing.List):
        """Callback for the subscription call.

        Notes:
            If there's already another consumer assigned to the partition we will get empty 'partitions';
            This func will be called after poll() will be called (not right after 'subscribe' call).
        """
        if not partitions:
            logger.warning("[Empty subscription].")
        else:
            logger.info(f"[Subscribed successfully]: partitions - {partitions}.")

    @staticmethod
    def on_revoke_callback(consumer, partitions):
        """Callback for the subscription call.

        Note:
            This func will be called after poll() will be called (not right after 'subscribe' call).
            After this function call re-subscription might be automatically made from the Kafka on some conditions.
        """
        logger.warning(
            f"[REVOKED subscription(s)] for partition(s) - {partitions}. "
            "If another consumer will unsubscribe - subscription will be renewed automatically."
        )

    def _receive_event(self, timeout=5) -> typing.Optional[bytes]:
        try:
            logger.debug("Start polling the message from queue...")
            msg = self.consumer.poll(timeout=timeout)
            logger.debug("Pooling was ended, checking returned data...")
        except Exception as e:
            logger.warning(f"Error polling: {e}")
            return None
        if msg is None:
            logger.warning(f"Polling timed out after {timeout} sec. No queue message was received.")
            return None
        if msg.error():
            # Error or event
            if msg.error().code() == KafkaError._PARTITION_EOF:
                # End of partition event
                logger.info(
                    f"{msg.topic()} [msg.partition()] reached end at offset {msg.offset()}"
                )
            else:
                # Error
                kafka_error = msg.error()
                ke = KafkaException(kafka_error)

                if kafka_error.code() in [KafkaError._TIMED_OUT_QUEUE, KafkaError._TIMED_OUT]:
                    # ordinary error messages when no message was received.
                    logger.warning(
                        f"[TIMED_OUT errors] no messages were consumed throughout timeout - {timeout} sec: {ke}"
                    )
                elif kafka_error.code() == KafkaError._TRANSPORT:
                    # when 'transport' was broken. Usually it'll be renewed automatically, but not all the time.
                    logger.error(f"[Broker transport failure] Calling to re-subscribe. Error: {ke}")

                    self.subscribe_to_topic()  # This is not 100% needed but it's better to have it here for now.
                else:
                    ke = KafkaException(kafka_error)
                    logger.error(f"Error occurred: {ke}")
            return None
        else:
            # Proper message
            return msg.value()

    def _receive_event_with_backoff(self, timeout_sec=300, backoff_sec=60) -> typing.Optional[Task]:
        """Poll queue for the Message with passed timeout.

        Args:
            timeout_sec: Maximum time to block waiting from queue for message, event or callback (seconds);
            backoff_sec: Time for Thread to sleep before next try to receive the Message from queue.
        """
        task: typing.Optional[Task] = None
        task_bytes = self._receive_event(timeout=timeout_sec)

        if not task_bytes:
            logger.info(
                f"No bytes in the message after polling with timeout - {timeout_sec} seconds. "
                f"Sleeping for backoff - {backoff_sec} seconds."
            )
            sleep(backoff_sec)
        else:
            task = deserialize_task(task_bytes)
            if not task:
                logger.error(f"Could not deserialize task\n Task bytes:{str(task_bytes)}")

        return task

    def get_task(self) -> typing.Optional[Task]:
        return self._receive_event_with_backoff(timeout_sec=self.poll_timeout_sec)
