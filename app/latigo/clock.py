import datetime
import math
from time import sleep

from pytz import utc

from latigo.utils import human_delta

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

    def closest_start_time(self, now: datetime.datetime) -> datetime.datetime:
        time_of_day = now.time()
        common_date = datetime.date(2019, 1, 1)
        p1 = datetime.datetime.combine(common_date, time_of_day, tzinfo=utc)
        p2 = datetime.datetime.combine(common_date, self.start_time, tzinfo=utc)
        from_start = p1 - p2
        interval_count = from_start / self.interval
        next_time = (math.floor(interval_count) + 1) * self.interval
        return datetime.datetime.combine(now.date(), self.start_time, tzinfo=utc) + next_time

    def time_left(self, now: datetime.datetime) -> datetime.timedelta:
        return self.closest_start_time(now=now) - now

    def wait_for_trigger(self):
        now = datetime.datetime.now(utc)
        iv = self.time_left(now=now)
        sec = iv.total_seconds()
        if sec > 0:
            logger.info(
                "Next prediction will occur at %s (in %s)",
                self.closest_start_time(now=now),
                human_delta(self.time_left(now=now))
            )
            logger.info(f"Waiting for {human_delta(iv)}")
            sleep(sec)

    def __str__(self):
        return (
            f"OnTheClockTimer(start_time={self.start_time}, interval={self.interval})"
        )
