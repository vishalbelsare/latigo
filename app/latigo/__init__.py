import os
from typing import Tuple
import pkg_resources
from latigo.utils import read_file

import logging

logger = logging.getLogger(__name__)


def _parse_version(version: str) -> Tuple[int, ...]:
    """
    Takes a string which starts with standard major.minor.patch.
    and returns the split of major and minor version as integers
    Parameters
    ----------
    version: str
        The semantic version string
    Returns
    -------
    Tuple[int, int]
        major and minor versions
    """
    return tuple(int(i) for i in version.split(".")[:2])


__version__ = "0.0.0"

latigo_path: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../app/"))
latigo_version_file = f"{latigo_path}/VERSION"

if pkg_resources.resource_exists(__name__, "VERSION"):
    __version__ = (
        pkg_resources.resource_string(__name__, "VERSION").decode("utf-8").strip()
    )
elif os.path.exists(latigo_version_file):
    __version__ = read_file(latigo_version_file)
else:
    # logger.warning("No version found")
    pass

MAJOR_VERSION, MINOR_VERSION = _parse_version(__version__)
