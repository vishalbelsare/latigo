import logging
import datetime
import time
import asyncio
from utils import *
from events import *
import traceback


class Scheduler:

    def __init__(self, out_connection_string, out_partition="0", debug=False):
        self.logger = logging.getLogger(__class__.__name__)
        self.configuration_sync_timer=Timer(datetime.timedelta(seconds=20))
        self.continuous_prediction_timer=Timer(datetime.timedelta(seconds=5))
        self.sender=EventSenderClient(out_connection_string, out_partition, debug)
        self.task_serial=0

    def synchronize_configuration(self):
        self.logger.info(f"Synchronizing configuration")

    def perform_prediction_step(self):
        self.logger.info(f"Performing prediction step")
        for i in range(10):
            data=f"Event {self.task_serial}".encode()
            self.logger.info(f"Generating '{data}' for {self.__class__.__name__}")
            self.sender.send_event(data)
            self.task_serial += 1


    def run(self):
        self.logger.info(f"Starting {self.__class__.__name__}")
        self.logger.info(f"Configuration sync: {self.configuration_sync_timer}")
        self.logger.info(f"Prediction step: {self.continuous_prediction_timer}")
        done=False
        while not done:
            try:
                if self.configuration_sync_timer.is_triggered():
                    # Restart timer
                    self.configuration_sync_timer.start()
                    # Do the configuratio sync
                    self.synchronize_configuration()

                if self.continuous_prediction_timer.is_triggered():
                    # Restart timer
                    self.continuous_prediction_timer.start()
                    # Do the prediction task queueing
                    self.perform_prediction_step()

                time.sleep(1)

            except KeyboardInterrupt:
                self.logger.info("Keyboard abort triggered, shutting down")
                done=True
            except Exception as e:
                self.logger.error("-----------------------------------")
                self.logger.error(f"Error occurred in scheduler: {e}")
                traceback.print_exc()
                self.logger.error("")
        self.logger.info(f"Stopping {self.__class__.__name__}")
