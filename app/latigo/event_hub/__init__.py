from latigo.log import setup_logging

from azure.eventhub.client import EventHubClient
from azure.eventhub import EventData, Offset

from latigo.utils import parse_event_hub_connection_string

from latigo.event_hub.offset_persistence import DBOffsetPersistance


class EventClient:

    def __init__(self, name, connection_string, debug=False):
        self.logger = setup_logging(__class__.__name__)
        self.debug = debug
        self.offset_persistence = DBOffsetPersistance(name)
        self.partition = "0"
        self.consumer_group = "$default"
        self.prefetch = 5000
        self.offset = Offset(self.offset_persistence.get())
        self.total = 0
        self.last_sn = -1
        self.client = None
        #self.logger.info(f"Event hub client credentials for {self.__class__.__name__}:")
        # pprint.pprint(parts)
        parts = parse_event_hub_connection_string(connection_string)
        if parts:
            self.address = f"amqps://{parts.get('endpoint')}/{parts.get('entity_path')}"
            self.username = parts.get('shared_access_key_name')
            self.password = parts.get('shared_access_key')
            self.debug = debug
            if not self.address:
                raise ValueError("No EventHubs URL supplied.")
            try:
                self.logger.info(f"Connecting to eventhub {self.address}")
                self.client = EventHubClient(
                    self.address,
                    debug=self.debug,
                    username=self.username,
                    password=self.password)

            except KeyboardInterrupt:
                pass
        else:
            raise Exception(
                f"Could not parse event hub connection string: {connection_string}")

    def __del__(self):
        if self.client:
            try:
                self.client.stop()
            except BaseException:
                raise

    def add_sender(self):
        try:
            return self.client.add_sender(partition=self.partition)
        except BaseException:
            raise

    def add_receiver(self):
        try:
            return self.client.add_receiver(
                consumer_group=self.consumer_group,
                partition=self.partition,
                prefetch=self.prefetch,
                offset=self.offset)
        except BaseException:
            raise

    def add_consumer(self):
        try:
            return self.client.create_consumer(
                consumer_group=self.consumer_group,
                partition=self.partition,
                offset=self.offset)
        except BaseException:
            raise

    def run(self):
        try:
            self.client.run()
        except BaseException:
            raise

    def send_event(self, event):
        try:
            self.sender.send(EventData(event))
        except BaseException:
            raise

    def recieve_single_event(self, timeout=100):
        try:
            event_data_list = self.receiver.receive(
                max_batch_size=1, timeout=timeout)
            if event_data_list:
                #self.logger.info(f"LEN: {len(list(event_data_list))}")
                event_data = event_data_list[0]
                self.last_offset = event_data.offset
                self.last_sn = event_data.sequence_number
                #self.logger.info("Received: {}, {}".format(last_offset, last_sn))
                self.total += 1
                return next(event_data.body)
        except BaseException:
            raise
