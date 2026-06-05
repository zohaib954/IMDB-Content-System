import pytest
import mongomock
from unittest.mock import patch, MagicMock
from app import create_app


@pytest.fixture
def app():
    app = create_app("testing")
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def mock_mongo_col():
    """Returns a real mongomock collection for unit tests."""
    client = mongomock.MongoClient()
    db = client["test_db"]
    return db["movies"]


@pytest.fixture
def mock_jobs_col():
    client = mongomock.MongoClient()
    db = client["test_db"]
    return db["upload_jobs"]


@pytest.fixture
def sample_csv_bytes():
    return """budget,homepage,original_language,original_title,overview,release_date,revenue,runtime,status,title,vote_average,vote_count,production_company_id,genre_id,languages
30000000,,en,Toy Story,A great movie,1995-10-30,373554033,81,Released,Toy Story,7.7,5415,3,16,['English']
65000000,,en,Jumanji,Another movie,1995-12-15,262797249,104,Released,Jumanji,6.9,2413,559,12,"['English', 'Français']"
"""