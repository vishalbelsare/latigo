from latigo.event_hub import EventClient


class EventSenderClient(EventClient):
    def __init__(self, name, connection_string, debug=False):
        super().__init__(name, connection_string, debug)
        self.sender = self.add_sender()
        self.run()
