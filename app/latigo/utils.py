import re
import pprint
import logging
from datetime import datetime, timedelta
import asyncio
import typing
import yaml


logger = logging.getLogger("latigo.utils")


def load_yaml(filename, output=False):

    with open(filename, "r") as stream:
        data = {}
        failure = None
        try:
            data = yaml.safe_load(stream)
        except Exception as e:
            logger.error(e)
            failure = e
            data = {}
        if output:
            pprint.pprint(data)
        return data, failure


def save_yaml(filename, data, output=False):

    with open(filename, "w") as stream:
        try:
            yaml.dump(data, stream, default_flow_style=False)
        except yaml.YAMLError as exc:
            logger.info(exc)
        if output:
            pprint.pprint(data)
        return data


def merge(source, destination):
    """
    run me with nosetests --with-doctest file.py

    >>> a = { 'first' : { 'all_rows' : { 'pass' : 'dog', 'number' : '1' } } }
    >>> b = { 'first' : { 'all_rows' : { 'fail' : 'cat', 'number' : '5' } } }
    >>> merge(b, a) == { 'first' : { 'all_rows' : { 'pass' : 'dog', 'fail' : 'cat', 'number' : '5' } } }
    True
    """
    for key, value in source.items():
        if isinstance(value, dict):
            # get node or create one
            node = destination.setdefault(key, {})
            merge(value, node)
        else:
            destination[key] = value


def parse_event_hub_connection_string(connection_string: str):
    if not connection_string:
        return None
    regex = r"Endpoint=sb://(?P<endpoint>.*)/;SharedAccessKeyName=(?P<shared_access_key_name>.*);SharedAccessKey=(?P<shared_access_key>.*);EntityPath=(?P<entity_path>.*)"
    matches = list(re.finditer(regex, connection_string))
    if len(matches) > 0:
        match = matches[0]
        return match.groupdict()


def parse_gordo_connection_string(connection_string: str):
    if not connection_string:
        return None
    # Rely on url_parse instead of regex for robustness while parsing url
    from urllib.parse import urlparse

    parts = urlparse(connection_string)
    regex = r"/gordo/(?P<gordo_version>v[0-9]*)/"
    matches = list(re.finditer(regex, parts.path))
    if len(matches) > 0:
        match = matches[0]
        data: typing.Dict[str, typing.Any] = match.groupdict()
        scheme = parts.scheme
        data["scheme"] = scheme
        data["host"] = parts.hostname
        # Since port is optional, we provide defaults based on scheme
        if parts.port:
            data["port"] = int(parts.port)
        else:
            data["port"] = 443 if scheme == "https" else 80
        return data


class Timer:
    def __init__(self, trigger_interval: timedelta):
        self.trigger_interval = trigger_interval
        self.start_time: typing.Optional[datetime] = None

    def start(self, start_time: typing.Optional[datetime] = None):
        if start_time:
            self.start_time = start_time
        else:
            self.start_time = datetime.now()

    def stop(self):
        self.start_time = None

    def interval(self) -> typing.Optional[timedelta]:
        if not self.start_time:
            return None
        return datetime.now() - self.start_time

    def is_triggered(self) -> bool:
        iv = self.interval()
        return True if not iv else (iv > self.trigger_interval)

    async def wait_for_trigger(self):
        iv = self.interval()
        if iv:
            await asyncio.sleep(iv)

    def __str__(self):
        return f"Timer(start_time={self.start_time}, trigger_interval={self.trigger_interval} {'[triggered]' if self.is_triggered() else ''})"
