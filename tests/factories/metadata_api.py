from datetime import datetime, timezone
from enum import Enum

import factory
from factory.fuzzy import FuzzyChoice

from latigo.metadata_api.data_structures import TimeSeriesIdMetadata, InputTag, OutputTag


class InputTagFactory(factory.Factory):
    name = factory.Sequence(lambda n: f"tag{n}")
    time_series_id = factory.Sequence(lambda n: f"{n:08}-{n:04}-{n:04}-{n:04}-{n:012}")

    class Meta:
        model = InputTag


class OutputTagTypeChoices(str, Enum):
    aggregated = "aggregated"
    derived = "derived"


class OutputTagFactory(factory.Factory):
    name = factory.Sequence(lambda n: f"name{n}|{n:08}-{n:04}-{n:04}-{n:04}-{n:012}|anomaly-confidence")
    time_series_id = factory.Sequence(lambda n: f"{n:08}-{n:04}-{n:04}-{n:04}-{n:012}")
    type = FuzzyChoice(OutputTagTypeChoices)
    description = factory.Sequence(lambda n: f"description{n}")
    derived_from = factory.Sequence(lambda n: f"derived{n}")

    class Meta:
        model = OutputTag


class TimeSeriesIdMetadataFactory(factory.Factory):
    project_name = factory.Sequence(lambda n: f"project{n:05}")
    model_name = factory.Sequence(lambda n: f"model{n:05}")
    revision = factory.Sequence(lambda n: f"revision{n:05}")
    training_time_from = factory.fuzzy.FuzzyDateTime(
        datetime(2020, 2, 1, 10, 0, tzinfo=timezone.utc), datetime(2020, 2, 10, 10, 30, tzinfo=timezone.utc),
    )
    training_time_to = factory.fuzzy.FuzzyDateTime(
        datetime(2020, 4, 1, 11, 0, tzinfo=timezone.utc), datetime(2020, 4, 10, 11, 30, tzinfo=timezone.utc),
    )
    input_tags = factory.List([factory.SubFactory(InputTagFactory) for _ in range(3)])
    output_tags = factory.List([factory.SubFactory(OutputTagFactory) for _ in range(5)])
    description = factory.Sequence(lambda n: f"Metadata description{n}")
    status = "not_defined"
    labels = None

    class Meta:
        model = TimeSeriesIdMetadata
