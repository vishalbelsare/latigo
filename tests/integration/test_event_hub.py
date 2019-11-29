import json
import pandas as pd
import typing
from datetime import datetime, timedelta
import logging
import pprint
from os import environ

from latigo.task_queue.kafka import KafkaTaskQueueSender, KafkaTaskQueueReceiver

logger = logging.getLogger(__name__)


def _get_config():
    not_found = "Not found in environment variables"
    # fmt: off
    return {
        "type": "kafka",
        "connection_string": environ.get("LATIGO_INTERNAL_EVENT_HUB", not_found),
        "security.protocol": "SASL_SSL",
        "ssl.ca.location": "/etc/pki/tls/certs/ca-bundle.crt", # Redhat?
        "sasl.mechanism": "PLAIN",
        "group.id": "1",
        "client.id": "latigo_scheduler",
        "request.timeout.ms": 10000,
        "session.timeout.ms": 10000,
        "default.topic.config": {"auto.offset.reset": "smallest"},
        "debug": "fetch",
        "topic": "latigo_topic",
        "enable.auto.commit": True,
        "auto.commit.interval.ms": 1000,
    }
    # fmt: on


def test_event_hub_write_read():
    config = _get_config()
    logger.info(config)
    logger.info("Instanciating kafka write client")
    ktqs = KafkaTaskQueueSender(config=config)
    logger.info("Instanciating kafka read client")
    ktqr = KafkaTaskQueueReceiver(config=config)
    send_msg = b"TEST MESSAGE"
    logger.info(f"SENDING MESSAGE: '{send_msg}'")
    msg = ktqs.send_event(send_msg)
    logger.info("Fetching message from kafka")
    ret_msg = ktqr.receive_event(timeout=2)
    logger.info(f"GOT MESSAGE: '{ret_msg}'")
    assert ret_msg == send_msg
    logger.info("Done")
