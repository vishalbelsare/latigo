from datetime import datetime
from typing import List


class OperationsPolicy:
    pass


class OperationsPolicyProviderInterface:
    def get_active_policies(self, from_time: datetime, to_time: datetime) -> List[OperationsPolicy]:
        pass


class MockOperationsPolicyProvider(OperationsPolicyProviderInterface):
    def get_active_policies(self, from_time: datetime, to_time: datetime) -> List[OperationsPolicy]:
        pass
