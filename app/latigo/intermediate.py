import logging
import pprint

import pandas as pd
import typing
from datetime import datetime, timedelta
from collections import namedtuple

from latigo.utils import rfc3339_from_datetime

logger = logging.getLogger(__name__)


class IntermediateFormat:
    def __init__(self):
        self.tag_names = []
        self.tag_names_map = {}
        self.tag_names_data: typing.Dict[str, typing.List] = {}

    def __len__(self):
        if self.tag_names and self.tag_names_data and len(self.tag_names) > 0:
            return len(self.tag_names_data[self.tag_names[0]])
        return 0

    def __getitem__(self, index):
        logger.info(f"GETTING: {index}")

    def from_time_series_api(self, items):
        if not items:
            logging.warning("No items")
            return None
        if not isinstance(items, typing.List):
            logging.warning("Items not a list")
            return None
        self.tag_names = []
        # Collect tag names in a list
        for i in range(len(items)):
            data = items[i]
            tag_name = data.get("name", None)
            # logger.info(f"TESTING DATA {i}:\n____DATA={data}\n_____TAG_NAME=({tag_name})")
            if not tag_name:
                continue
            self.tag_names.append(tag_name)
        self.tag_names_map = {}
        self.tag_names_data = {}
        index = 0
        # Create tag name to index map
        for tag_name in self.tag_names:
            self.tag_names_map[tag_name] = index
            self.tag_names_data[tag_name] = []
            index += 1
        # Pack time series data by tag_name
        for i in range(len(items)):
            data = items[i]
            tag_name = data.get("name", None)
            if not tag_name:
                continue
            datapoints = data.get("datapoints", None)
            for datapoint in datapoints:
                if not datapoint:
                    continue
                value = datapoint.get("value", None)
                if not value:
                    continue
                if tag_name in self.tag_names_data:
                    self.tag_names_data[tag_name].append(value)

    def _count_series_size(self):
        BIG = 100000000
        self.series_len = BIG
        for tag_name in self.tag_names:
            if tag_name in self.tag_names:
                l = len(self.tag_names_data[tag_name])
                self.series_len = l if l < self.series_len else self.series_len
        if BIG == self.series_len:
            self.series_len = 0

    def _select_gordo_tags(self, tags: typing.List):
        data = []
        self._count_series_size()
        tl_len = len(tags)
        for i in range(self.series_len):
            line = []
            for tag_name in tags:
                tag_data = self.tag_names_data.get(tag_name, [])
                if tag_data and len(tag_data) >= i:
                    value = tag_data[i]
                    line.append(value)
            data.append(line)
        return data

    def to_gordo(self, tags: typing.List, target_tags: typing.List):
        gordo_data_x = self._select_gordo_tags(tags)
        gordo_data_y = self._select_gordo_tags(target_tags)
        return {"X": gordo_data_x, "Y": gordo_data_y}
