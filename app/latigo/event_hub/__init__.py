import logging

from azure.eventhub.client import EventHubClient
from azure.eventhub import EventData, Offset

from latigo.utils import parse_event_hub_connection_string

from latigo.event_hub.offset_persistence import DBOffsetPersistance

logger = logging.getLogger(__name__)


class EventClient:
    def __init__(self, name, connection_string, debug=False):
        self.name = name
        self.debug = debug
        self.offset_persistence = DBOffsetPersistance(name)
        self.partition = "0"
        self.consumer_group = "$default"
        self.prefetch = 5000
        self.last_offset = Offset(0)
        self.load_offset()
        self.total = 0
        self.last_sn = -1
        self.client = None
        parts = parse_event_hub_connection_string(connection_string)
        if parts:
            self.address = f"amqps://{parts.get('endpoint')}/{parts.get('entity_path')}"
            self.username = parts.get("shared_access_key_name")
            self.password = parts.get("shared_access_key")
            self.debug = debug
            if not self.address:
                raise ValueError("No EventHubs URL supplied.")
            try:
                logger.info(f"Connecting to eventhub {self.address}")
                self.client = EventHubClient(self.address, debug=self.debug, username=self.username, password=self.password)
            except KeyboardInterrupt:
                pass
        else:
            raise Exception(f"Could not parse event hub connection string: {connection_string}")

    def load_offset(self):
        offset = self.offset_persistence.get()
        # Make sure we have valid offset
        if not offset:
            offset = "0"
        logger.info(f"Loaded offset for {self.name} was {offset}")
        self.last_offset = Offset(offset)

    def store_offset(self):
        # Make sure we have valid offset
        offset = self.last_offset
        if not offset:
            offset = Offset("0")
        self.offset_persistence.set(offset.__dict__.get("value", "0"))
        logger.info(f"Stored offset for {self.name} was {offset}")

    def __del__(self):
        if self.client:
            try:
                self.client.stop()
            except BaseException:
                raise

    def add_sender(self):
        try:
            logger.info(f"Adding sender to {self.name} with partition={self.partition}")
            return self.client.add_sender(partition=self.partition)
        except BaseException:
            raise

    def add_receiver(self):
        try:
            logger.info(f"Adding receiver to {self.name} with consumer_group={self.consumer_group}, partition={self.partition}, prefetch={self.prefetch}, offset={self.last_offset}")
            return self.client.add_receiver(consumer_group=self.consumer_group, partition=self.partition, prefetch=self.prefetch, offset=self.last_offset)
        except BaseException:
            raise

    def add_consumer(self):
        try:
            logger.info(f"Adding consumer to {self.name} with consumer_group={self.consumer_group}, partition={self.partition}, offset={self.last_offset}")
            return self.client.create_consumer(consumer_group=self.consumer_group, partition=self.partition, offset=self.last_offset)
        except BaseException:
            raise

    def run(self):
        try:
            logger.info(f"Running {self.name}")
            self.client.run()
            logger.info(f"Run completed for {self.name}")
        except BaseException:
            raise

    def send_event(self, event):
        try:
            self.sender.send(EventData(event))
        except BaseException:
            raise

    def receive_event(self, timeout=100):
        try:
            event_data_list = self.receiver.receive(max_batch_size=1, timeout=timeout)
            if event_data_list:
                # logger.info(f"LEN: {len(list(event_data_list))}")
                event_data = event_data_list[0]
                self.last_offset = event_data.offset
                self.store_offset()
                self.last_sn = event_data.sequence_number
                # logger.info("Received: {}, {}".format(last_offset, last_sn))
                self.total += 1
                return next(event_data.body)
        except BaseException:
            raise
