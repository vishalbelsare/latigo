from latigo.metadata_api.client import MetadataAPIClient


def test_get(metadata_client: MetadataAPIClient):
    url = f"{metadata_client.base_url}/ready"
    res = metadata_client.get(url=url)

    assert res.status_code == 200
    assert res.text == "Ok"
