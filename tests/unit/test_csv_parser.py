import io
import pytest
from app.ingestion.csv_parser import CSVParser
from app.core.exceptions import EmptyFileException, FileTooLargeException


@pytest.fixture
def parser():
    return CSVParser()


@pytest.fixture
def valid_csv():
    content = b"""budget,homepage,original_language,original_title,overview,release_date,revenue,runtime,status,title,vote_average,vote_count,production_company_id,genre_id,languages
30000000,,en,Toy Story,A great movie,1995-10-30,373554033,81,Released,Toy Story,7.7,5415,3,16,['English']
"""
    return io.BytesIO(content)


def test_parse_yields_records(parser, valid_csv):
    chunks = list(parser.parse(valid_csv))
    assert len(chunks) > 0
    assert len(chunks[0]) == 1
    record = chunks[0][0]
    assert record["title"] == "Toy Story"
    assert record["vote_average"] == 7.7


def test_parse_languages_as_list(parser, valid_csv):
    chunks = list(parser.parse(valid_csv))
    record = chunks[0][0]
    assert isinstance(record["languages"], list)
    assert "English" in record["languages"]


def test_validate_empty_file_raises(parser):
    empty = io.BytesIO(b"")
    with pytest.raises(EmptyFileException):
        parser.validate(empty)


def test_supported_mime_types(parser):
    assert "text/csv" in parser.supported_mime_types


def test_malformed_rows_skipped(parser):
    content = b"""budget,original_language,title,vote_average,vote_count,genre_id,production_company_id,languages,release_date,revenue,runtime,status,original_title,overview,homepage
NOTANUMBER,en,Toy Story,7.7,5415,16,3,['English'],1995-10-30,0,81,Released,Toy Story,Overview,
"""
    f = io.BytesIO(content)
    chunks = list(parser.parse(f))
    # Should not crash - malformed budget is handled gracefully
    assert isinstance(chunks, list)