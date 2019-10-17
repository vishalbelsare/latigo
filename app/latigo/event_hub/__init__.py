import logging

from azure.eventhub.client import EventHubClient
from azure.eventhub import EventData, Offset

from latigo.utils import parse_event_hub_connection_string

from latigo.event_hub.offset_persistence import DBOffsetPersistance, MemoryOffsetPersistance

logger = logging.getLogger(__name__)


class EventClient:
    def _prepare_offset_peristance(self):
        self.offset_persistance_config = self.config.get("offset_persistence", None)
        if not self.offset_persistance_config:
            logger.info(self.config)
            raise Exception("No offset_persistance_config specified")
        offset_persistance_type = self.offset_persistance_config.get("type", None)
        offset_persistance_name = self.offset_persistance_config.get("name", "unnamed")
        self.offset_persistence = None
        if "db" == offset_persistance_type:
            self.offset_persistence = DBOffsetPersistance(self.offset_persistance_config)
        elif "memory" == offset_persistance_type:
            self.offset_persistence = MemoryOffsetPersistance()

    def __init__(self, config: dict):
        self.client = None
        if not config:
            raise Exception("No config specified")
        self.config = config
        self.name = self.config.get("name", "unnamed")
        self.connection_string = self.config.get("connection_string", None)
        self.do_trace = self.config.get("do_trace", False)
        self.partition = self.config.get("partition", "0")
        self.consumer_group = self.config.get("consumer_group", "$default")
        self.prefetch = self.config.get("prefetch", 5000)
        self._prepare_offset_peristance()
        self.last_offset = Offset(0)
        self.load_offset()
        self.total = 0
        self.last_sn = -1
        if not self.connection_string:
            raise Exception("No connection string specified")
        parts = parse_event_hub_connection_string(self.connection_string)
        if parts:
            self.address = f"amqps://{parts.get('endpoint')}/{parts.get('entity_path')}"
            self.username = parts.get("shared_access_key_name")
            self.password = parts.get("shared_access_key")
            if not self.address:
                raise ValueError("No EventHubs URL supplied.")
            try:
                logger.info(f"Connecting to eventhub {self.address}")
                self.client = EventHubClient(self.address, debug=self.do_trace, username=self.username, password=self.password)
            except KeyboardInterrupt:
                pass
        else:
            raise Exception(f"Could not parse event hub connection string: {self.connection_string}")

    def __del__(self):
        if self.client:
            try:
                self.client.stop()
            except BaseException:
                raise

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
