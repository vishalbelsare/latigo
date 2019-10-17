from latigo.event_hub import EventClient


class EventSenderClient(EventClient):
    def __init__(self, config: dict):
        super().__init__(config)
        self.sender = self.add_sender()
        self.run()
