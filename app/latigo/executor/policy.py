from typing import List

class OperationsPolicy:
    pass


class OperationsPolicyProviderInterface:
    def get_active_policies(from_time: timestamp, to_time:timestamp) -> List(OperationsPolicy)


class MockOperationsPolicyProvider(OperationsPolicyProviderInterface):
    def get_active_policies(from_time: timestamp, to_time:timestamp) -> List(OperationsPolicy)
