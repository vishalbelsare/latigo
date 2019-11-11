from os import environ

# NOTE: This must be started before the imports
# Set up memory database (no file)
environ["LATIGO_INTERNAL_DATABASE"] = "sqlite://"

from latigo.task_queue.event_hub import EventHubTaskQueueSender, EventHubTaskQueueReceiver

connection_string = environ.get("LATIGO_INTERNAL_EVENT_HUB", None)

test_event = "TEST EVENT 123"


class TestEventHub:
    def test_event_sender_client(self):
        if connection_string:
            config = {"connection_string": connection_string, "name": "sender_test_task_queue", "do_trace": True, "offset_persistence": {"type": "memory", "name": "arnold"}}
            sender = EventHubTaskQueueSender(config)
            sender.send_event(test_event)

    def test_event_receiver_client(self):
        if connection_string:
            config = {"connection_string": connection_string, "name": "receiver_test_task_queue", "do_trace": True, "offset_persistence": {"type": "memory", "name": "arnold"}}
            receiver = EventHubTaskQueueReceiver(config)
            received_event = receiver.receive_event()
            assert received_event == test_event
