

class OperationsPolicy:
    pass


class OperationsPolicyProviderInterface:
    def get_active_policies(from: timestamp, to:timestamp) -> list(OperationsPolicy)


class MockOperationsPolicyProvider(OperationsPolicyProviderInterface):
    def get_active_policies(from: timestamp, to:timestamp) -> list(OperationsPolicy)
