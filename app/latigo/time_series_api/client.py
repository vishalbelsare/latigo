import logging
import typing

from latigo.types import TimeRange

from ..utils import get_batches
from .cache import TagMetadataCache
from .misc import _itemes_present, get_auth_session, parse_request_json

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
            raise Exception("TimeSeriesAPIClient failed. Please see previous errors for clues as to why")

    def _get(self, *args, **kwargs):
        return self.session.get(*args, **kwargs)

    def _post(self, *args, **kwargs):
        return self.session.post(*args, **kwargs)

    def _patch(self, *args, **kwargs):
        return self.session.patch(*args, **kwargs)

    def _fetch_data_for_id(self, tag_id: str, time_range: TimeRange) -> typing.Dict:
        """Fetch data points for tag id.

        Note:
            if "includeOutsidePoints" is True then -> points immediately prior to and following the time window will
                be included in result and following data filtering before sending for the prediction should be made.
        """
        url = f"{self.base_url}/{tag_id}/data"
        params = {
            "startTime": time_range.rfc3339_from(),
            "endTime": time_range.rfc3339_to(),
            "limit": 100000,
            "includeOutsidePoints": False,
        }
        res = self._get(url=url, params=params)
        return parse_request_json(res)

    def _fetch_data_for_multiple_ids(
        self, tag_ids: typing.Iterable[str], time_range: TimeRange
    ) -> typing.List[typing.Dict]:
        """Fetch data points for multiple tag ids (max 100).

        Docs: https://api.equinor.com/docs/services/Timeseries-api-v1-6
            /operations/getMultiDatapoints

        Note:
            - if "includeOutsidePoints" is True then -> points
                immediately prior to and following the time window will
                be included in result and following data filtering before
                sending for the prediction should be made.
            - if more then 100 "tag ids" will be sent to API - error
                code is returned: {"statusCode":400}.
        """
        url = f"{self.base_url}/query/data"
        max_ids_in_one_request = 100
        tags_data = []

        for batch in get_batches(tag_ids, batch_size=max_ids_in_one_request):
            request_data = [
                {
                    "id": tag_id,
                    "startTime": time_range.rfc3339_from(),
                    "endTime": time_range.rfc3339_to(),
                    "limit": 100000,
                    "includeOutsidePoints": False,
                }
                for tag_id in batch
            ]
            rep_data = parse_request_json(self._post(url=url, json=request_data))
            tags_data.extend(rep_data["data"]["items"])

        return tags_data

    def _get_metadata_from_api(self, name: str, facility: typing.Optional[str] = None) -> typing.Dict:
        """Fetch metadata from Time Series API.

        Args:
            - name: name of the tag. Example: "1901.A-21T.MA_Y".
            - facility: name of the facility where tag belongs to.
                It should has value or should not be passed to the API.

        Note: !never use 'asset_id' in query, gordo provides asset_ids
            that are not incompatible with TimeSeries api.
        """
        if not name:
            raise ValueError("No tag name is specified for fetching from Time Series API.")

        body = {"name": name, "facility": facility} if facility else {"name": name}
        res = self._get(self.base_url, params=body)
        return parse_request_json(res)

    def get_meta_by_name(self, name: str, facility: typing.Optional[str] = None) -> typing.Dict:
        meta = self._tag_metadata_cache.get_metadata(name, facility)
        if meta:
            return meta

        # get from Time Series API and store to cache
        meta = self._get_metadata_from_api(name, facility)
        if meta:
            self._tag_metadata_cache.set_metadata(name, facility, meta)
        return meta

    def _create_id(
        self, name: str, facility: str, description: str = "", unit: str = "", external_id: str = "",
    ) -> dict:
        """Create timeseries tag object.

        Args:
            name: timeseries object name to be created (tag name).
            facility: for now we assume that "facility" is
                the same for us as "asset".
            description: is not used for now.
            unit: is not used for now.
            external_id: is not used for now.
        """
        body = {
            "name": name,
            "description": description,
            "step": True,
            "unit": unit,
            "facility": facility,
            "externalId": external_id,
        }
        res = self._post(self.base_url, json=body, params=None)
        return parse_request_json(res)

    def _create_id_if_not_exists(
        self, name: str, facility: str, description: str = "", unit: str = "", external_id: str = "",
    ) -> dict:
        meta = self.get_meta_by_name(name=name, facility=facility)
        if meta and _itemes_present(meta):
            return meta
        return self._create_id(
            name=name, facility=facility, description=description, unit=unit, external_id=external_id
        )

    def _store_data_for_id(self, id: str, datapoints: typing.List[typing.Dict[str, str]]) -> dict:
        body = {"datapoints": datapoints}
        url = f"{self.base_url}/{id}/data"
        res = self._post(url, json=body, params=None)
        return parse_request_json(res)

    def store_multiple_datapoints(self, datapoints_to_store: typing.List[typing.Dict[str, typing.Any]]) -> dict:
        """Save prediction results for multiple tag_ids.

        Docs:
            API_URL/operations/writeMultipleData?&groupBy=tag

        Args:
            - datapoints_to_store: ts_ids with datapoints to store.
                [
                    {
                        "id": "dd7d8481-81a3-407f-95f0-a2f1cb382a4b",
                        "datapoints": [
                            {
                                "time": "string",
                                "value": 0.0,
                                "status": 192
                            }
                        ]
                    }
                ]
        """
        url = f"{self.base_url}/data"
        body = {"items": datapoints_to_store}

        res = self._post(url=url, json=body)
        return parse_request_json(res)

    def replace_cached_metadata_with_new(self, tag_name: str, facility: str, description: str) -> dict:
        """Fetch new tag metadata from TS API and replace it in cache.

        Args:
            - tag_name: name of the tag. Example: "1901.A-21TE28.MA_Y";
            - facility: internal TS project identifier. Example: "1000";
            - description: tag description.
        """
        # get from TS API
        meta = self._get_metadata_from_api(tag_name)

        if not meta["data"]["items"]:
            # if not exists create in TS
            meta = self._create_id(name=tag_name, facility=facility, description=description)

        if not meta["data"]["items"]:
            raise ValueError(f"Could not replace cached metadata for {tag_name}/{facility}/{description}")

        # set in cache with new value
        self._tag_metadata_cache.set_metadata(tag_name, facility, meta)
        return meta

    def fetch_tag_by_id(self, ts_id: str):
        """Get Tag by its ID."""
        url = f"{self.base_url}/{ts_id}"

        res = self._get(url=url)
        return parse_request_json(res)

    def patch_tag_facility_by_id(self, ts_id: str, facility: str):
        """Change Tag facility on new one."""
        url = f"{self.base_url}/{ts_id}"
        body = {"facility": facility}

        res = self._patch(url=url, json=body)
        return parse_request_json(res)

    def get_facility_by_tag_name(self, tag_name: str) -> str:
        """Fetch "facility" of the tag timeseries object.

        Raise:
            - ValueError if no items were found.
            - ValueError if more then one tag with such name were found.
            - ValueError if 'facility' is missing.
        """
        res = self.get_meta_by_name(name=tag_name)
        ts_tag = self.get_only_item_from_metadata(metadata=res, tag_name=tag_name)
        facility = ts_tag["facility"]
        if not facility:
            raise ValueError(f"tag 'facility' is empty for tag name '{tag_name}' with data: {ts_tag}")
        return facility

    @staticmethod
    def get_only_item_from_metadata(metadata: dict, tag_name: str) -> dict:
        """Validate and return only one (only) item from metadata.

        Args:
            - metadata: response of the TS API with tag objects.
                {
                    "data": {
                        "items": [
                            {
                                "id": "7f4c7d71-0000-4aa6-0000",
                                "name": "R-29F.CA",
                                "assetId": "JSVC",
                                "facility": "1000",
                                ...
                            },
                            {
                                ...
                            }
                        ]
                    }
                }
            - tag_name: name of the tag that is looked for.

        Raise:
            - ValueError if no items were found.
            - ValueError if more then one tag with such name was found.

        Return:
            tag object.
        """
        items = metadata["data"]["items"]
        if not items:
            raise ValueError(f"No tag object were found in TS API for tag name '{tag_name}'")
        if len(items) > 1:
            raise ValueError(f"More then 1 tag object were found in TS API for tag name '{tag_name}'. Data: {items}")
        return items[0]
