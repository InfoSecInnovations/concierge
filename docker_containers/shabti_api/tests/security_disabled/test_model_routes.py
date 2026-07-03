async def test_get_models_with_tags(shabti_client):
    response = shabti_client.get("/models", params={"tags": ["chat"]})
    assert response.status_code == 200
    assert all("tags" in x and "chat" in x["tags"] for x in response.json()["data"])
