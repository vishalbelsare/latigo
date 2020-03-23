from latigo.metadata_api.client import MetadataAPIClient


def test_get(metadata_client: MetadataAPIClient):
    url = f"{metadata_client.base_url}/ready"
    res = metadata_client.get(url=url)

    assert res.status_code == 200
    assert res.text == "Ok"


# response_data = {
#     'project_name': 'string', 'model_name': 'string', 'revision': 'string', 'status': 'not_defined',
#     'description': 'string', 'training_time_from': '2020-03-19T15:00:02.156000+00:00',
#     'training_time_to': '2020-03-19T15:00:02.156000+00:00', 'labels': ['string'],
#     'input_tags': [{'name': 'string', 'time_series_id': 'string'}],
#     'output_tags': [{'name': 'string', 'time_series_id': 'string', 'type': 'aggregated', 'derived_from': 'string',
#                      'description': 'string'}],
#     'model_id': 1}


# def test_send_time_series_id_metadata(metadata_client: MetadataAPIClient):
#     res = metadata_client.send_time_series_id_metadata()
#     assert res is None
