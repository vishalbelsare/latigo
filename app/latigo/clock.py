import datetime
import typing
import pprint
import math
import asyncio
from latigo.utils import sleep, human_delta

import logging

logger = logging.getLogger(__name__)


class OnTheClockTimer:
    """
    Class to provide a schedule from time of day + recurring interval as starting point
    Also provides convenience methods to make it easy to keep track of this schedule
    """

    def __init__(self, start_time: datetime.time, interval: datetime.timedelta):
        self.start_time = start_time
        self.interval = interval

    def closest_start_time(
        self, now: datetime.datetime = datetime.datetime.now()
    ) -> datetime.datetime:
        time_of_day = now.time()
        common_date = datetime.date(2019, 1, 1)
        p1 = datetime.datetime.combine(common_date, time_of_day)
        p2 = datetime.datetime.combine(common_date, self.start_time)
        from_start = p1 - p2
        interval_count = from_start / self.interval
        next_time = (math.floor(interval_count) + 1) * self.interval
        # logger.info(f"DATE: {now.date()}, TIME:{now.time()}, from_start:{from_start}, interval_count:{interval_count}, last_time={last_time}, next_time={next_time}")
        return datetime.datetime.combine(now.date(), self.start_time) + next_time

    def time_left(
        self, now: datetime.datetime = datetime.datetime.now()
    ) -> datetime.timedelta:
        return self.closest_start_time(now=now) - now

    def wait_for_trigger(self, now: datetime.datetime = datetime.datetime.now()):
        iv = self.time_left(now=now)
        sec = iv.total_seconds()
        if sec > 0:
            logger.info(f"Waiting for {human_delta(iv)}")
            sleep(sec)
        return True

    def __str__(self):
        return (
            f"OnTheClockTimer(start_time={self.start_time}, interval={self.interval})"
        )
