import datetime
import logging
import os.path
import pprint
import re
import traceback
import typing
from concurrent.futures import wait
from concurrent.futures.thread import ThreadPoolExecutor
from functools import lru_cache, reduce
from typing import Dict

import pytz
import yaml

import latigo.rfc3339
from latigo.log import measure

logger = logging.getLogger(__name__)
THREAD_POOL_EXECUTOR_WORKERS = 10


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
) -> typing.Tuple[typing.Dict, typing.Optional[str]]:

    defaults_config = None
    if defaults_filename:
        defaults_config, defaults_failure = load_yaml(defaults_filename, output)
        if not defaults_config:
            return (
                {},
                f"Could not load defaults configuration from {defaults_filename}: {defaults_failure}",
            )

    base_config = None
    if base_filename:
        base_config, base_failure = load_yaml(base_filename, output)
        if not base_config:
            return (
                {},
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
        if ms >= period_ms:
            period_value, ms = divmod(ms, period_ms)
            # has_s = "s" if period_value > 1 else ""
            # strings.append("%s %s%s" % (period_value, period_name, has_s))
            strings.append(f"{period_value} {period_name}")
            ct += 1
            if max > 0 and ct > max:
                break
    return sign + ", ".join(strings)  # + f"({td_object}, {ms})"


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


def local_datetime_to_utc_as_str(target: datetime) -> str:
    """Make datetime string representation in UTC timezone. Use it just for local time!

    Return:
         String representation of without and taking into the account time zone formatted in UTC timezone.
            Do not make changes if already in UTC timezone or does not have any.
    """
    if target.tzinfo is None or not target.utcoffset() or target.tzinfo == pytz.utc:
        target = target.replace(tzinfo=datetime.timezone.utc)
        return target.isoformat()

    utc_offset_timedelta = datetime.datetime.utcnow() - datetime.datetime.now()
    target = target.replace(tzinfo=datetime.timezone.utc)
    result_utc_datetime = target + utc_offset_timedelta
    return result_utc_datetime.isoformat()


def datetime_to_utc_as_str(target: datetime) -> str:
    """Make datetime string representation in UTC timezone.

    Return:
        String representation of without and taking into the account time zone formatted in UTC timezone.
            If no timezone - UTC timezone will be added.
        Examples:
            - 2020-04-03 05:00:07.086149+00:00 -> 2020-04-03T05:00:07.086149+00:00
            - 2020-04-03 05:00:07.086149+02:00 -> 2020-04-03T03:00:07.086149+00:00
    """
    if target.tzinfo is None or not target.utcoffset() or target.tzinfo == pytz.utc:
        target = target.replace(tzinfo=datetime.timezone.utc)
        return target.isoformat()

    # to this part we should get only datetime with particular timezone offset
    res = target.astimezone(pytz.utc).replace(tzinfo=datetime.timezone.utc)
    return res.isoformat()


def get_nested_config_value(dictionary: Dict, *keys):
    return reduce(lambda d, key: d.get(key) if d else None, keys, dictionary)


@lru_cache(maxsize=1, typed=True)
def get_thread_pool_executor(max_workers: int = THREAD_POOL_EXECUTOR_WORKERS):
    """Return Singleton instance of the Executor to run tasks on.

    Args:
        max_workers: amount of workers to run tasks with.
            Do not set "max_workers" to the big number.
    """
    return ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="latigo-thread-pool-")


@measure("run_async_in_threads_executor")
def run_async_in_threads_executor(
    functions: typing.List[typing.Tuple[typing.Callable, tuple]]
) -> typing.List[typing.Any]:
    """Run functions with it args in the thread poll.

    Use it only for I/O-bound tasks like API calls.

    Args:
        functions: (func to call, args to be passed to the func)

    Return:
        Results of the functions execution in RANDOM order.
    """
    executor = get_thread_pool_executor()
    tasks = [executor.submit(func, *args) for func, args in functions]

    done, _ = wait(tasks)
    return [func.result() for func in done]


def get_batches(iterable, batch_size: int = 10) -> typing.Generator:
    """Split iterable to the batches.

    Example:
        [1, 2, 3, 4, 5] with batch_size == 2 -> (1, 2), (3, 4), (5, ).
    """
    items_amount = len(iterable)
    for i in range(0, items_amount, batch_size):
        yield iterable[i:min(i + batch_size, items_amount)]
