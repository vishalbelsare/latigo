import yaml
import re
import pprint
import logging
import datetime
from os import environ


def print_env():
    for k, v in environ.items():
        print(f"ENVIRONMENT: {k} = {v}")


def load_yaml(filename, output=False):

    with open(filename, 'r') as stream:
        data = {}
        failure = None
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as e:
            logger = logging.getLogger('utils.load_yaml')
            logger.error(e)
            failure = e
            data = {}
        if output:
            pprint.pprint(data)
        return data, failure


def save_yaml(filename, data, output=False):

    with open(filename, 'w') as stream:
        try:
            yaml.dump(data, stream, default_flow_style=False)
        except yaml.YAMLError as exc:
            logger = logging.getLogger('utils.save_yaml')
            logger.info(exc)
        if output:
            pprint.pprint(data)
        return data


def parse_event_hub_connection_string(connection_string: str):
    if not connection_string:
        return None
    regex = r"Endpoint=sb://(?P<endpoint>.*)/;SharedAccessKeyName=(?P<shared_access_key_name>.*);SharedAccessKey=(?P<shared_access_key>.*);EntityPath=(?P<entity_path>.*)"
    matches = list(re.finditer(regex, connection_string))
    if len(matches) > 0:
        match = matches[0]
        return match.groupdict()


class Timer:

    def __init__(self, trigger_interval: datetime.timedelta):
        self.logger = logging.getLogger(__class__.__name__)
        self.trigger_interval = trigger_interval
        self.start_time = None

    def start(self, start_time: datetime.datetime = None):
        self.start_time = start_time if start_time else datetime.datetime.now()

    def stop(self):
        self.start_time = None

    def interval(self) -> datetime.timedelta:
        if not self.start_time:
            return None
        return datetime.datetime.now() - self.start_time

    def is_triggered(self) -> bool:
        iv = self.interval()
        return True if not iv else (iv > self.trigger_interval)

    async def wait_for_trigger(self):
        iv = self.interval()
        if iv:
            await asyncio.sleep(iv)

    def __str__(self):
        return f"Timer(start_time={self.start_time}, trigger_interval={self.trigger_interval} {'[triggered]' if self.is_triggered() else ''})"
