from latigo.event_hub.send import EventSenderClient
from os import environ

# Set up memory database (no file)
environ['LATIGO_INTERNAL_DATABASE'] = "sqlite://"


class TestEventHub:

    def test_event_sender_client(self):
        connection_string = ""
        sender = EventSenderClient(connection_string)
        test_event = "TEST EVENT 123"
        sender.send_event(test_event)
