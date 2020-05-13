from datetime import datetime, timezone

import factory
from factory.fuzzy import FuzzyChoice

from latigo.types import Task


class TaskFactory(factory.Factory):
    project_name = factory.Sequence(lambda n: f"project{n:05}")
    model_name = factory.Sequence(lambda n: f"model{n:05}")
    from_time = factory.fuzzy.FuzzyDateTime(
        datetime(2020, 4, 20, 10, 0, tzinfo=timezone.utc),
        datetime(2020, 4, 20, 10, 30, tzinfo=timezone.utc),
    )
    to_time = factory.fuzzy.FuzzyDateTime(
        datetime(2020, 4, 20, 11, 0, tzinfo=timezone.utc),
        datetime(2020, 4, 20, 11, 30, tzinfo=timezone.utc),
    )

    class Meta:
        model = Task
