import logging
import typing

import inject
import ujson
from redis import StrictRedis

logger = logging.getLogger(__name__)


class TagMetadataCache:
    """Storing and fetching tag metadata in Redis cache.

    Tag metadata is almost never changed, but sometimes it could.
    Cause of this we need to set TTL parameter and handle data changing.
    """

    CACHE_TIME_TO_LIVE = 86400  # in seconds == 24 hours

    def __init__(self):
        self._cache = inject.instance(StrictRedis)  # was initialized in the executor.py

    def get_metadata(self, name: str, facility: typing.Optional[str]) -> typing.Optional[typing.Dict]:
        """Fetch tag metadata from cache if exists.

        Args:
            - name: name of the tag. Example: "1901.A-21TE28.MA_Y";
            - facility: TS internal project identifier. Example: "1000".
        """
        key = self._make_metadata_key(name, facility)

        res = self._cache.get(key)
        if res:
            res = ujson.loads(res)
        return res

    def set_metadata(self, name: str, facility: typing.Optional[str], meta: typing.Dict):
        """Set tag metadata to cache (overrides if exists).

        Args:
            - name: name of the tag. Example: "1901.A-21TE28.MA_Y";
            - facility: TS internal project identifier. Example: "1000".
        """
        key = self._make_metadata_key(name, facility)
        dumped_meta = ujson.dumps(meta)

        res = self._cache.set(name=key, value=dumped_meta, ex=self.CACHE_TIME_TO_LIVE)
        if not res:
            raise Exception(f"Failed to store key '{key}' with value '{meta}' to cache.")

    @staticmethod
    def _make_metadata_key(name: str, facility: typing.Optional[str]):
        return f"{facility}::{name}"
