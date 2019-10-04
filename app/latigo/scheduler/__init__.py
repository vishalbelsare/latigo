from latigo.log import setup_logging
from os import environ
from datetime import timedelta
import time
import pickle
import traceback
from latigo.utils import Timer
from latigo.sensor_data import Task
from latigo.event_hub.send import EventSenderClient


class Scheduler:

    def __init__(self):
        self.logger = setup_logging(__class__.__name__)

        self.out_connection_string = environ.get(
            'LATIGO_INTERNAL_EVENT_HUB', None)
        if not self.out_connection_string:
            raise Exception(
                "No connection string specified for internal event hub. Please set environment variable LATIGO_INTERNAL_EVENT_HUB to valid connection string")
        self.debug = False
        self.configuration_sync_timer = Timer(timedelta(seconds=20))
        self.continuous_prediction_timer = Timer(timedelta(seconds=5))
        self.sender = EventSenderClient(self.out_connection_string, self.debug)
        self.task_serial = 0

    def synchronize_configuration(self):
        self.logger.info(f"Synchronizing configuration")

    def perform_prediction_step(self):
        self.logger.info(f"Performing prediction step")
        for i in range(10):
            task = Task(f"Task {self.task_serial}")
            #self.logger.info(f"SENDING TASK: {task}")
            #self.logger.info(f"Generating '{task}' for {self.__class__.__name__}")
            task_bytes = pickle.dumps(task)
            #self.logger.info(f"SENDING DATA: {pformat(task_bytes)}")
            try:
                self.sender.send_event(task_bytes)
                self.task_serial += 1
            except Exception as e:
                self.logger.error(f"Could not send task: {e}")
                traceback.print_exc()

    def run(self):
        self.logger.info(f"Starting {self.__class__.__name__}")
        self.logger.info(
            f"Configuration sync: {self.configuration_sync_timer}")
        self.logger.info(
            f"Prediction step: {self.continuous_prediction_timer}")
        done = False
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
                done = True
            except Exception as e:
                self.logger.error("-----------------------------------")
                self.logger.error(f"Error occurred in scheduler: {e}")
                traceback.print_exc()
                self.logger.error("")
        self.logger.info(f"Stopping {self.__class__.__name__}")
