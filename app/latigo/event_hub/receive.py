import time
import asyncio

from latigo.event_hub import EventClient


class EventReceiveClient(EventClient):
    def __init__(self, config: dict):
        super().__init__(config)
        self.receiver = self.add_receiver()
        self.run()

    def receive_event_with_backoff(self, timeout=100, backoff=1000):
        event_data = self.receive_event(timeout)
        if not event_data:
            time.sleep(backoff)
        return event_data


class EventConsumerClient(EventClient):
    def __init__(self, config: dict):
        super().__init__(config)
        self.consumer = self.add_consumer()
        loop = asyncio.get_event_loop()
        timeout = 100
        loop.run_until_complete(self.consume_events(timeout))

    async def consume_events(self, callback, timeout=100):
        async with self.consumer:
            total = 0
            start_time = time.time()
            for event_data in await self.consumer.receive(timeout=timeout):
                self.last_offset = event_data.offset.selector()
                last_sn = event_data.sequence_number
                self.logger.info("Received: {}, {}".format(self.last_offset, last_sn))
                self.store_offset()
                if callback:
                    callback(event_data)
                total += 1
            end_time = time.time()
            run_time = end_time - start_time
            self.logger.info("Received {} messages in {} seconds".format(total, run_time))
