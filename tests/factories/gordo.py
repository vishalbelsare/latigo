from datetime import datetime, timezone

import factory
from factory.fuzzy import FuzzyChoice
from gordo.machine import Machine


class MachineDatasetFactory(factory.Factory):
    train_start_date = factory.fuzzy.FuzzyDateTime(
        datetime(2020, 2, 20, 10, 0, tzinfo=timezone.utc), datetime(2020, 2, 20, 10, 30, tzinfo=timezone.utc),
    )
    train_end_date = factory.fuzzy.FuzzyDateTime(
        datetime(2020, 4, 20, 11, 0, tzinfo=timezone.utc), datetime(2020, 4, 20, 11, 30, tzinfo=timezone.utc),
    )
    tag_list = factory.List("GRA-QTR1-13-0853.PV" for _ in range(3))
    target_tag_list = factory.List("GRA-QTR1-13-0853.PV" for _ in range(3))

    class Meta:
        model = dict


class MachineFactory(factory.Factory):
    name = factory.Sequence(lambda n: f"{n:08}-{n:04}-{n:03}-{n:04}-{n:012}-{n:04}")
    project_name = factory.Sequence(lambda n: f"project{n:03}")
    dataset = factory.SubFactory(MachineDatasetFactory)
    model = {}

    class Meta:
        model = Machine
