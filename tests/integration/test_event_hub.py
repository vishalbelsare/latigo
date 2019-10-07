from os import environ

# NOTE: This must be started befoer the imports
# Set up memory database (no file)
environ["LATIGO_INTERNAL_DATABASE"] = "sqlite://"

from latigo.event_hub.send import EventSenderClient
from latigo.event_hub.receive import EventReceiveClient

connection_string = environ["LATIGO_INTERNAL_EVENT_HUB"]

test_event = "TEST EVENT 123"


class TestEventHub:
    def test_event_sender_client(self):
        sender = EventSenderClient("test", connection_string)
        sender.send_event(test_event)

    def test_event_receiver_client(self):
        receiver = EventReceiveClient("test", connection_string)
        received_event = receiver.receive_event()
        assert received_event == test_event
