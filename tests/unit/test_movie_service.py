import io
import pytest
import mongomock
from unittest.mock import MagicMock, patch

from app.movies.repository import MovieRepository
from app.movies.service import MovieService


@pytest.fixture
def mock_collections():
    client = mongomock.MongoClient()
    db = client["test_db"]
    return db["movies"], db["upload_jobs"]


@pytest.fixture
def service(mock_collections):
    movies_col, jobs_col = mock_collections
    repo = MovieRepository(movies_col)
    return MovieService(repo, jobs_col), movies_col, jobs_col


def test_upload_sync_returns_stats(service):
    svc, movies_col, _ = service
    csv_content = b"""budget,homepage,original_language,original_title,overview,release_date,revenue,runtime,status,title,vote_average,vote_count,production_company_id,genre_id,languages
30000000,,en,Toy Story,Overview,1995-10-30,0,81,Released,Toy Story,7.7,5415,3,16,['English']
"""
    f = io.BytesIO(csv_content)
    f.name = "test.csv"
    result = svc.upload_sync(f, "test.csv", "text/csv")
    assert result["total_inserted"] == 1
    assert result["mode"] == "sync"
    assert "processing_time_seconds" in result


def test_list_movies_pagination(service):
    svc, movies_col, _ = service
    # Insert 5 test records directly
    movies_col.insert_many([
        {"title": f"Movie {i}", "vote_average": float(i), "languages": ["English"],
         "release_date": f"200{i}-01-01", "original_language": "en"}
        for i in range(5)
    ])
    result = svc.list_movies(None, None, None, page=1, page_size=2)
    assert result["page_size"] == 2
    assert result["total"] == 5
    assert result["total_pages"] == 3
    assert len(result["items"]) == 2


def test_list_movies_filter_by_year(service):
    svc, movies_col, _ = service
    movies_col.insert_many([
        {"title": "Old Movie", "release_date": "1990-05-01", "languages": ["English"], "vote_average": 5.0},
        {"title": "New Movie", "release_date": "2020-05-01", "languages": ["English"], "vote_average": 7.0},
    ])
    result = svc.list_movies(year=2020, language=None, sort_by=None, page=1, page_size=10)
    assert result["total"] == 1
    assert result["items"][0]["title"] == "New Movie"


def test_list_movies_filter_by_language(service):
    svc, movies_col, _ = service
    movies_col.insert_many([
        {"title": "French Film", "languages": ["Français"], "release_date": "2020-01-01", "vote_average": 6.0},
        {"title": "English Film", "languages": ["English"], "release_date": "2020-01-01", "vote_average": 7.0},
    ])
    result = svc.list_movies(year=None, language="English", sort_by=None, page=1, page_size=10)
    assert result["total"] == 1
    assert result["items"][0]["title"] == "English Film"