# pylint: disable=C0413
from latigo.log import setup_logging

logger = setup_logging(__name__)

# pylint: disable=C0413
import traceback
import pickle
import time
from datetime import timedelta
from os import environ
from latigo.event_hub.send import EventSenderClient
from latigo.sensor_data import Task
from latigo.utils import Timer


class Scheduler:
    def __init__(self):
        self.out_connection_string = environ.get("LATIGO_INTERNAL_EVENT_HUB", None)
        if not self.out_connection_string:
            raise Exception("No connection string specified for internal event hub. Please set environment variable LATIGO_INTERNAL_EVENT_HUB to valid connection string")
        self.debug = False
        self.configuration_sync_timer = Timer(timedelta(seconds=20))
        self.continuous_prediction_timer = Timer(timedelta(seconds=5))
        self.sender = EventSenderClient(self.out_connection_string, self.debug)
        self.task_serial = 0

    def synchronize_configuration(self):
        logger.info(f"Synchronizing configuration")

    def perform_prediction_step(self):
        logger.info(f"Performing prediction step")
        for i in range(10):
            task = Task(f"Task {self.task_serial}")
            # logger.info(f"SENDING TASK: {task}")
            # logger.info(f"Generating '{task}' for {self.__class__.__name__}")
            task_bytes = pickle.dumps(task)
            # logger.info(f"SENDING DATA: {pformat(task_bytes)}")
            try:
                self.sender.send_event(task_bytes)
                self.task_serial += 1
            except Exception as e:
                logger.error(f"Could not send task: {e}")
                traceback.print_exc()

    def run(self):
        logger.info(f"Starting {self.__class__.__name__}")
        logger.info(f"Configuration sync: {self.configuration_sync_timer}")
        logger.info(f"Prediction step: {self.continuous_prediction_timer}")
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
                logger.info("Keyboard abort triggered, shutting down")
                done = True
            except Exception as e:
                logger.error("-----------------------------------")
                logger.error(f"Error occurred in scheduler: {e}")
                traceback.print_exc()
                logger.error("")
        logger.info(f"Stopping {self.__class__.__name__}")
