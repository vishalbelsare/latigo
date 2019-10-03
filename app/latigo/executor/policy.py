from typing import List
from datetime import datetime


class OperationsPolicy:
    pass


class OperationsPolicyProviderInterface:
    def get_active_policies(from_time: datetime,
                            to_time: datetime) -> List(OperationsPolicy):
        pass


class MockOperationsPolicyProvider(OperationsPolicyProviderInterface):
    def get_active_policies(from_time: datetime,
                            to_time: datetime) -> List(OperationsPolicy):
        pass
