from unittest.mock import MagicMock, Mock, patch, call

from requests import Response

store_data_for_id_resp = {"statusCode": 200}


@patch("latigo.time_series_api.prediction_storage_provider.rfc3339_from_datetime", new=Mock(side_effect=lambda x: x))
def test_put_prediction(prediction_data, prediction_storage, tag_metadata):
    with patch.object(prediction_storage, "_get_metadata_from_api", return_value=tag_metadata), patch.object(
        prediction_storage, "_store_data_for_id", return_value=store_data_for_id_resp
    ), patch.object(
        prediction_storage, "get_facility_by_tag_name", return_value="1903"
    ):
        output_tag_names, output_time_series_ids = prediction_storage.put_prediction(prediction_data)

    expected_output_tag_names = {
        ("model-output", "1903.R1"): "1903.R1|model|model-output",
        ("model-output", "1903.R2"): "1903.R2|model|model-output",
        ("confidence", ""): "1903.INDICATOR|model|confidence",
    }
    expected_output_time_series_ids = {
        ("model-output", "1903.R1"): "tag_id",
        ("model-output", "1903.R2"): "tag_id",
        ("confidence", ""): "tag_id",
    }

    assert (output_tag_names, output_time_series_ids) == (expected_output_tag_names, expected_output_time_series_ids)


@patch("latigo.time_series_api.prediction_storage_provider.rfc3339_from_datetime", new=Mock(side_effect=lambda x: x))
def test_put_prediction_409_error(prediction_storage, prediction_data, tag_metadata):
    exception_response = Response()
    exception_response.status_code = 409
    exception_response.reason = "Conflict url"

    with patch.object(prediction_storage, "_get", new=MagicMock(return_value=exception_response)), patch.object(
        prediction_storage, "replace_cached_metadata_with_new", return_value=tag_metadata
    ) as replace_cached_mock, patch.object(
        prediction_storage, "_store_data_for_id", return_value=store_data_for_id_resp
    ), patch.object(prediction_storage, "get_facility_by_tag_name", return_value="1903"):
        res = prediction_storage.put_prediction(prediction_data)

    calls = [
        call(facility="1903", description="Gordo model-output - 1903.R1", tag_name="1903.R1|model|model-output"),
        call(facility="1903", description="Gordo model-output - 1903.R2", tag_name="1903.R2|model|model-output"),
        call(facility="1903", description="Gordo confidence - ", tag_name="1903.INDICATOR|model|confidence"),
    ]
    replace_cached_mock.assert_has_calls(calls)
    assert res
