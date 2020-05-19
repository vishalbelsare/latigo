"""Exceptions for the Time Series logic."""
from typing import List


class NoCommonAssetFound(Exception):
    """Raise if no 'common asset' found in dateframe column headers."""

    def __init__(self, column_values: List):
        self.message = (
            "No common asset found in dataframe columns. " f"Parsed data: {'; '.join(col[1] for col in column_values)}"
        )
        super().__init__(self.message)
