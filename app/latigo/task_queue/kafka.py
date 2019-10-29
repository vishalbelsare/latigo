import sys
import getopt
import json
import logging
import sys
import pprint
import time
from confluent_kafka import Producer, Consumer, KafkaException, KafkaError
from confluent_kafka.admin import AdminClient, NewTopic
from latigo.utils import parse_event_hub_connection_string
from latigo.task_queue import Task, deserialize_task, serialize_task, TaskQueueSenderInterface, TaskQueueReceiverInterface

logger = logging.getLogger(__name__)


def stats_callback(stats_json_str):
    stats_json = json.loads(stats_json_str)
    logger.info("\nKAFKA Stats: {}\n".format(pprint.pformat(stats_json)))


def delivery_callback(err, msg):
    if err:
        logger.warning(f"Message failed delivery: {err} ({msg.topic()} [{msg.partition()}] @ {msg.offset()})")
    else:
        pass
        # logger.info(f"Message delivered to {msg.topic()} [{msg.partition()}] @ {msg.offset()}")


def prepare_kafka_config(config: dict):
    parts = parse_event_hub_connection_string(config.get("connection_string")) or {}
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
        "enable.auto.commit": config.get("enable.auto.commit"), "auto.commit.interval.ms": config.get("auto.commit.interval.ms"), "default.topic.config": config.get("default.topic.config"), "debug": config.get("debug")}
    # fmt: on


class KafkaTaskQueueSender(TaskQueueSenderInterface):
    # This is not possible in Azure as it is expected you create your topics (a.k.a. event hubs)
    # Manually in Azure portal, or using azure proprietary APIs
    def _create_topics(self):
        # Create Admin instance
        self.admin = AdminClient(self.config)
        # Create topics
        fs = self.admin.create_topics([NewTopic(topic, num_partitions=3, replication_factor=1) for topic in [self.topic]])
        # Wait for topic creation to complete
        for topic, f in fs.items():
            try:
                logger.info(f"Waiting for topic '{topic}' to be created")
                f.result()  # The result itself is None
                logger.info(f"Topic '{topic}' created")
            except Exception as e:
                logger.error(f"Failed to create topic '{topic}': {e}")

    def __init__(self, config: dict):
        # Producer configuration
        # See https://github.com/edenhill/librdkafka/blob/master/CONFIGURATION.md
        # See https://github.com/edenhill/librdkafka/wiki/Using-SSL-with-librdkafka#prerequisites for SSL issues
        self.config = prepare_kafka_config(config)
        # Find our topic
        parts = parse_event_hub_connection_string(config.get("connection_string")) or {}
        self.topic = parts.get("entity_path")
        # self._create_topics()
        # Create Producer instance
        self.producer = Producer(self.config)

        # Wait until all messages have been delivered
        logger.info(f"Waiting for {len(self.producer)} deliveries")
        self.producer.flush()

    def __del__(self):
        if self.producer:
            self.producer.close()

    def put_task(self, task: Task):
        try:
            task_bytes = serialize_task(task)
            if task_bytes:
                self.producer.produce(self.topic, task_bytes, callback=delivery_callback)
            else:
                raise Exception("Could not serialize task")
        except BufferError as e:
            logger.info(f"Local producer queue is full ({len(self.producer)} messages awaiting delivery): try again")
        self.producer.poll(0)


def print_assignment(consumer, partitions):
    print("Assignment:", partitions)


class KafkaTaskQueueReceiver(TaskQueueReceiverInterface):
    def __init__(self, config: dict):
        # Consumer configuration
        # See https://github.com/edenhill/librdkafka/blob/master/CONFIGURATION.md
        self.config = prepare_kafka_config(config)
        # Find our topic
        parts = parse_event_hub_connection_string(config.get("connection_string")) or {}
        self.topic = parts.get("entity_path")
        # Create Consumer instance
        self.consumer = Consumer(self.config)
        # Subscribe to topics
        self.consumer.subscribe([self.topic], on_assign=print_assignment)

    def __del__(self):
        if self.consumer:
            self.consumer.close()

    def receive_event(self, timeout=100):
        msg = self.consumer.poll(timeout=timeout)
        if msg is None:
            return None
        if msg.error():
            # Error or event
            if msg.error().code() == KafkaError._PARTITION_EOF:
                # End of partition event
                logger.info(f"{msg.topic()} [msg.partition()] reached end at offset {msg.offset()}")
            else:
                # Error
                e = KafkaException(msg.error())
                # raise e
                logger.error(f"Error occurred: {e}")
        else:
            # Proper message
            return msg.value()

    def receive_event_with_backoff(self, timeout=100, backoff=1000):
        task_bytes = self.receive_event(timeout)
        task = None
        if not task_bytes:
            time.sleep(backoff)
        else:
            task = deserialize_task(task_bytes)
        if not task:
            logger.error("Could not deserialize task")
        return task

    def get_task(self) -> Task:
        return self.receive_event_with_backoff()
