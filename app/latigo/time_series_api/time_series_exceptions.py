"""Exceptions for the Time Series logic."""
from pandas import MultiIndex


class NoCommonAssetFound(Exception):
    """Raise if no 'common asset' found in dateframe column headers."""

    def __init__(self, columns: MultiIndex):
        self.message = (
            "No common asset found in dataframe columns. " f"Parsed data: {'; '.join(col[1] for col in columns.values)}"
        )
        super().__init__(self.message)
