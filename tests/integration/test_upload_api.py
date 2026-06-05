import io
import pytest
from unittest.mock import patch, MagicMock


SAMPLE_CSV = (
    "budget,homepage,original_language,original_title,overview,release_date,"
    "revenue,runtime,status,title,vote_average,vote_count,production_company_id,genre_id,languages\n"
    "30000000,,en,Toy Story,Overview,1995-10-30,373554033,81,Released,Toy Story,7.7,5415,3,16,['English']\n"
    "65000000,,en,Jumanji,Overview,1995-12-15,262797249,104,Released,Jumanji,6.9,2413,559,12,\"['English', 'Francais']\"\n"
).encode("utf-8")


@patch("app.movies.routes.mongo")
def test_sync_upload_success(mock_mongo, client):
    mock_db = MagicMock()
    mock_mongo.db = mock_db
    mock_db["movies"].insert_many.return_value = MagicMock(inserted_ids=["id1", "id2"])
    mock_db["movies"].create_index = MagicMock()

    data = {"file": (io.BytesIO(SAMPLE_CSV), "movies.csv", "text/csv")}
    response = client.post(
        "/api/v1/movies/upload/sync",
        data=data,
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["data"]["mode"] == "sync"


@patch("app.movies.routes.mongo")
def test_sync_upload_no_file(mock_mongo, client):
    response = client.post("/api/v1/movies/upload/sync")
    assert response.status_code == 400
    assert response.get_json()["success"] is False


@patch("app.movies.routes.mongo")
def test_sync_upload_wrong_mime(mock_mongo, client):
    data = {"file": (io.BytesIO(b"fake content"), "data.json", "application/json")}
    response = client.post(
        "/api/v1/movies/upload/sync",
        data=data,
        content_type="multipart/form-data",
    )
    assert response.status_code == 415


@patch("app.movies.routes.mongo")
def test_movies_list_default_pagination(mock_mongo, client):
    mock_db = MagicMock()
    mock_mongo.db = mock_db
    mock_db["movies"].count_documents.return_value = 0
    mock_db["movies"].find.return_value.sort.return_value.skip.return_value.limit.return_value = []
    mock_db["movies"].find.return_value.skip.return_value.limit.return_value = []

    response = client.get("/api/v1/movies/")
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["success"] is True
    assert "meta" in json_data


@patch("app.movies.routes.mongo")
def test_movies_list_invalid_sort(mock_mongo, client):
    response = client.get("/api/v1/movies/?sort_by=invalid_field")
    assert response.status_code == 400


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200