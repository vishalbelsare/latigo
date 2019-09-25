import logging
import re
import pprint

from azure.eventhub.client import EventHubClient
#from azure.eventhub import EventHubSharedKeyCredential
from azure.eventhub import Sender, EventData, Offset



class EventClient:

    def __init__(self, connection_string, partition="0", debug=False):
        self.logger = logging.getLogger(__class__.__name__)
        parts = parse_event_hub_connection_string(connection_string)
        self.logger.info(f"Event hub client credentials for {self.__class__.__name__}:")
        # pprint.pprint(parts)

        self.address=f"amqps://{parts.get('endpoint')}/{parts.get('entity_path')}"
        self.username=parts.get('shared_access_key_name')
        self.password=parts.get('shared_access_key')
        self.debug=debug
        self.partition=partition
        self.client=None
        if not self.address:
            raise ValueError("No EventHubs URL supplied.")
        try:
            self.logger.info(f"Connecting to eventhub {self.address}")
            self.client = EventHubClient(self.address, debug=self.debug, username=self.username, password=self.password)

        except KeyboardInterrupt:
            pass

    def __del__(self):
        if self.client:
           try:
               self.client.stop()
           except:
               raise


class EventSenderClient(EventClient):

    def __init__(self, connection_string, partition="0", debug=False):
        super().__init__(connection_string, partition, debug)
        try:
            self.sender = self.client.add_sender(partition = self.partition)
            self.client.run()
        except:
            raise

    def send_event(self, event):
        try:
            self.sender.send(EventData(event))
        except:
            raise

class EventReceiveClient(EventClient):

    def __init__(self, connection_string, partition="0", consumer_group="$default", prefetch=5000, offset="-1", debug=False):
        super().__init__(connection_string, partition, debug)
        self.consumer_group=consumer_group
        self.partition=partition
        self.prefetch=prefetch
        self.offset=Offset(offset)

        self.total = 0
        self.last_sn = -1
        vlast_offset = "-1"
        try:
            self.receiver = self.client.add_receiver(consumer_group=self.consumer_group, partition=self.partition, prefetch=self.prefetch, offset=self.offset)
            self.client.run()
        except:
            raise

    def recieve_event(self, timeout=100):
        try:
            event_data_list = self.receiver.receive(max_batch_size=1, timeout = timeout)
            if event_data_list:
                #self.logger.info(f"LEN: {len(list(event_data_list))}")
                event_data=event_data_list[0]

                self.last_offset = event_data.offset
                self.last_sn = event_data.sequence_number
                #self.logger.info("Received: {}, {}".format(last_offset, last_sn))
                self.total += 1
                return next(event_data.body)
            else:
                time.sleep(1000)
        except:
            raise

class EventConsumerClient(EventClient):
    def __init__(self, connection_string, partition="0", consumer_group="$default", offset="-1", debug=False):
        super().__init__(connection_string, partition, debug)
        self.consumer_group=consumer_group
        self.partition=partition
        self.offset=Offset(offset)

        self.total = 0
        self.last_sn = -1
        vlast_offset = "-1"
        try:
            self.consumer = self.client.create_consumer(consumer_group=self.consumer_group, partition=self.partition, offset=self.offset)
        except:
            raise
        loop = asyncio.get_event_loop()
        timeout=100
        loop.run_until_complete(self.consume_events(timeout))

    async def consume_events(self, callback, timeout=100):
        async with self.consumer:
            total = 0
            start_time = time.time()
            for event_data in await consumer.receive(timeout=timeout):
                last_offset = event_data.offset
                last_sn = event_data.sequence_number
                self.logger.info("Received: {}, {}".format(last_offset, last_sn))
                if callback:
                    callback(event_data)
                total += 1
            end_time = time.time()
            run_time = end_time - start_time
            self.logger.info("Received {} messages in {} seconds".format(total, run_time))

