import re
import pprint
import logging
import datetime
import yaml
import typing
import sys
import time
import os.path
import typing
import traceback

import latigo.rfc3339


logger = logging.getLogger(__name__)


def rfc3339_from_datetime(date_object: datetime.datetime) -> str:
    return latigo.rfc3339.timetostr(date_object)


def datetime_from_rfc3339(date_string: str) -> datetime.datetime:
    return latigo.rfc3339.parse_datetime(date_string)


def load_yaml(filename, output=False):
    if not os.path.exists(filename):
        return None, f"File did not exist: '{filename}'."
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
        if not os.path.exists(filename):
            return None, f"File was not written: '{filename}'."
        return data


def find_missing(
    source: typing.Dict[typing.Any, typing.Any], parent: typing.Optional[str] = None
):
    """
    Generate list of keys with missing values in multi-level dictionary

    source: Dict[Any, Any]
        The dictionary to walk and look for missing values
    parent: Optional[str]
        The parent key from the previous iteration, if any.

    Returns
    -------
    missing: List[str]
        List of keys as JSON paths whose values are `None`.

    Example
    -------
    >>> find_missing({"a": True, "b":{"c": None, "d": False}, "e": None})
    ["b.c", "e"]
    """
    missing: typing.List[str] = list()
    for k, v in source.items():
        k = f"{parent}.{k}" if parent else k
        if type(v) is dict:
            missing += find_missing(v, k)
        elif v is None:
            missing.append(k)
    return missing


def remove_missing(source: typing.Dict[typing.Any, typing.Any]):
    """
    Remove keys from a multi-level dictionary whose values are `None`

    source: dict
        The dictionary to walk and remove keys with `None` values.

    Returns
    -------
    destination: List[str]
        Dictionary with keys removed whose values were 'None'.

    Example
    -------
    >>> remove_missing({"a": True, "b":{"c": None, "d": False}, "e": None})
    {"a": True, "b":{"d": False}}
    """
    destination: typing.Dict[typing.Any, typing.Any] = dict()
    for k, v in source.items():
        if type(v) is dict:
            destination[k] = remove_missing(v)
        elif v is not None:
            destination[k] = v
    return destination


def merge(source, destination, skip_none=True):
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
            merge(value, node, skip_none)
        else:
            if not skip_none or value:
                destination[key] = value


def load_configs(
    defaults_filename: str = None,
    base_filename: str = None,
    overlay_config: dict = None,
    output: bool = False,
) -> typing.Tuple[typing.Optional[typing.Dict], typing.Optional[str]]:

    defaults_config = None
    if defaults_filename:
        defaults_config, defaults_failure = load_yaml(defaults_filename, output)
        if not defaults_config:
            return (
                None,
                f"Could not load defaults configuration from {defaults_filename}: {defaults_failure}",
            )

    base_config = None
    if base_filename:
        base_config, base_failure = load_yaml(base_filename, output)
        if not base_config:
            return (
                None,
                f"Could not load base configuration from {base_filename}: {base_failure}",
            )

    # Start empty handed
    config: dict = {}
    # Add defaults
    if defaults_config:
        merge(defaults_config, config, False)
    # Add base
    if base_config:
        merge(base_config, config, True)
    # Add overlay
    if overlay_config:
        merge(overlay_config, config, True)
    return config, None


def parse_event_hub_connection_string(connection_string: str):
    if not connection_string:
        return None
    regex = r"Endpoint=sb://(?P<endpoint>.*)/;SharedAccessKeyName=(?P<shared_access_key_name>.*);SharedAccessKey=(?P<shared_access_key>.*);EntityPath=(?P<entity_path>.*)"
    matches = list(re.finditer(regex, connection_string))
    if len(matches) > 0:
        match = matches[0]
        return match.groupdict()
    else:
        logger.warning(f"No matches for {regex}")
        return None


def parse_gordo_connection_string(connection_string: str):
    if not connection_string:
        return None
    # Rely on url_parse instead of regex for robustness while parsing url
    from urllib.parse import urlparse

    parts = urlparse(connection_string)
    regex = r"/gordo/(?P<gordo_version>v[0-9]*)"
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
    else:
        logger.warning(f"No matches for {regex}")
        return None


def human_delta(td_object: datetime.timedelta, max: int = 0):
    ms = int(td_object.total_seconds() * 1000)
    if ms == 0:
        return "0 ms"
    sign = ""
    if ms < 0:
        ms = -ms
        sign = "-"
    # fmt: off
    periods = [
        ("year",  1000 * 60 * 60 * 24 * 365),
        ("month", 1000 * 60 * 60 * 24 * 30),
        ("day",   1000 * 60 * 60 * 24),
        ("hr",    1000 * 60 * 60),
        ("min",   1000 * 60),
        ("sec",   1000),
        ("ms", 1)
    ]
    # fmt: on

    strings = []
    ct: int = 0
    for period_name, period_ms in periods:
        if ms > period_ms:
            period_value, ms = divmod(ms, period_ms)
            # has_s = "s" if period_value > 1 else ""
            # strings.append("%s %s%s" % (period_value, period_name, has_s))
            strings.append(f"{period_value} {period_name}")
            ct += 1
            if max > 0 and ct > max:
                break
    return sign + ", ".join(strings)  # + f"({td_object}, {ms})"


def list_loggers():
    loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
    for l in loggers:
        logger.info(f"LOGGER: {l}")


def sleep(time_sec):
    time.sleep(time_sec)
    # await asyncio.sleep async


def print_process_info():
    if hasattr(os, "getppid"):
        print(f"Parent process:{os.getppid()}")
    print(f"Process id:{os.getpid()}")


def read_file(fname, strip=True):
    fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), fname)
    data = ""
    if os.path.exists(fn):
        with open(fn) as f:
            data = f.read()
            data = data.strip() if strip else data
    return data


def format_error(e):
    return traceback.format_exception(type(e), e, e.__traceback__)
