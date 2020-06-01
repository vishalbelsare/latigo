import logging
import typing

from oauthlib.oauth2.rfc6749.errors import MissingTokenError

from latigo.types import TimeRange

from .cache import TagMetadataCache
from .misc import _itemes_present, _parse_request_json, get_auth_session

logger = logging.getLogger(__name__)


class TimeSeriesAPIClient:
    """Client to connect with Time Series API.

    Info: "Historian" is the on-premises TS database ("source") that TS
        export data from and make it available in the TA API.
        This is where most of the data from TS API is coming from.

        So the TS names you see in the API are defined in the Historian.
        The names can change for many reasons:
            - a TS record was created with a wrong name;
            - changes in the engineering numbering systems;
            - cleaning and improving the naming;
            - etc.
        An example: renamed from "name" to "name-old" /
        "name-x" indicating that the TS record is not active anymore.
    """

    def __str__(self):
        return f"TimeSeriesAPIClient({self.base_url})"

    def _fail(self, message):
        self.good_to_go = False
        logger.error(message)
        logger.warning("Using config:")
        logger.warning(self.config)
        return None

    def _parse_base_url(self):
        self.base_url = self.config.get("base_url", None)
        if not self.base_url:
            return self._fail("No base_url found in config")

    def _create_session(self, force: bool = False):
        self.session = get_auth_session(self.auth_config, force)
        if not self.session:
            return self._fail(f"Could not create session with force={force}")

    def _parse_auth_config(self):
        self.auth_config = self.config.get("auth", dict())
        if not self.auth_config:
            return self._fail("No auth_config found in config")
        self._create_session(force=False)

    def __init__(self, config: dict):
        self.good_to_go = True
        self._tag_metadata_cache = TagMetadataCache()
        self.config = config
        if not self.config:
            raise Exception("No config specified")
        self._parse_auth_config()
        self._parse_base_url()
        self.do_async = self.config.get("async", False)
        if not self.good_to_go:
            raise Exception(
                "TimeSeriesAPIClient failed. Please see previous errors for clues as to why"
            )

    def _get(self, *args, **kwargs):
        res = None
        try:
            res = self.session.get(*args, **kwargs)
        except MissingTokenError:
            logger.info("Token expired, retrying GET after recreating session")
            self._create_session(force=True)
            res = self.session.get(*args, **kwargs)
        return res

    def _post(self, *args, **kwargs):
        res = None
        try:
            res = self.session.post(*args, **kwargs)
        except MissingTokenError:
            logger.info("Token expired, retrying POST after recreating session")
            self._create_session(force=True)
            res = self.session.post(*args, **kwargs)
        return res

    def _fetch_data_for_id(
        self, id: str, time_range: TimeRange
    ) -> typing.Tuple[typing.Optional[typing.Dict], typing.Optional[str]]:
        """Fetch data points for tag id.

        Note:
            if "includeOutsidePoints" is True then -> points immediately prior to and following the time window will
                be included in result and following data filtering before sending for the prediction should be made.
        """
        url = f"{self.base_url}/{id}/data"
        params = {
            "startTime": time_range.rfc3339_from(),
            "endTime": time_range.rfc3339_to(),
            "limit": 100000,
            "includeOutsidePoints": False,
        }
        res = self._get(url=url, params=params)
        return _parse_request_json(res)

    def _get_metadata_from_api(self, name: str) -> typing.Tuple[typing.Optional[typing.Dict], typing.Optional[str]]:
        """Fetch metadata from Time Series API.

        Args:
            - name: name of the tag. Example: "1901.A-21T.MA_Y".

        Note: !never use 'asset_id' in query, gordo provides asset_ids
            that might be incompatible with time series api.
        """
        if not name:
            raise ValueError("No tag name is specified for fetching from Time Series API.")

        body = {"name": name}
        res = self._get(self.base_url, params=body)
        return _parse_request_json(res)

    def get_meta_by_name(
        self, name: str, asset_id: str
    ) -> typing.Tuple[typing.Optional[typing.Dict], typing.Optional[str]]:
        meta = self._tag_metadata_cache.get_metadata(name, asset_id)
        if meta:
            return meta, None

        # get from Time Series API and store to cache
        meta, msg = self._get_metadata_from_api(name)
        if meta:
            self._tag_metadata_cache.set_metadata(name, asset_id, meta)
        return meta, msg

    def _create_id(
        self,
        name: str,
        description: str = "",
        unit: str = "",
        asset_id: str = "",
        external_id: str = "",
    ):
        body = {
            "name": name,
            "description": description,
            "step": True,
            "unit": unit,
            "assetId": asset_id,
            "externalId": external_id,
        }
        res = self._post(self.base_url, json=body, params=None)
        return _parse_request_json(res)

    def _create_id_if_not_exists(
        self, name: str, asset_id: str, description: str = "", unit: str = "", external_id: str = "",
    ):
        meta, err = self.get_meta_by_name(name=name, asset_id=asset_id)
        if meta and _itemes_present(meta):
            return meta, err
        return self._create_id(name, description, unit, asset_id, external_id)

    def _store_data_for_id(self, id: str, datapoints: typing.List[typing.Dict[str, str]]):
        body = {"datapoints": datapoints}
        url = f"{self.base_url}/{id}/data"
        res = self._post(url, json=body, params=None)
        return _parse_request_json(res)

    def replace_cached_metadata_with_new(self, tag_name: str, asset_id: str, description: str):
        """Fetch new tag metadata from TS API and replace it in cache.

        Args:
            - tag_name: name of the tag. Example: "1901.A-21TE28.MA_Y";
            - asset_id: asset/project identifier. Example: "1000";
            - description: tag description.
        """
        # get from TS API
        meta, err = self._get_metadata_from_api(tag_name)
        if not meta:
            # if not exists create in TS
            meta, err = self._create_id(asset_id, description, asset_id)

        if not meta:
            raise ValueError(f"Could not replace cached metadata for {tag_name}/{asset_id}/{description}")

        # set in cache with new value
        self._tag_metadata_cache.set_metadata(tag_name, asset_id, meta)
        return meta, err
