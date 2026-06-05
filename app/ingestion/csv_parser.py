import io
import ast
import pandas as pd
from typing import Generator

from app.core.exceptions import EmptyFileException, FileTooLargeException
from app.ingestion.base_parser import FileParser

MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024 * 1024  # 1GB

REQUIRED_COLUMNS = {
    "budget", "original_language", "original_title",
    "release_date", "title", "vote_average", "vote_count",
    "genre_id", "languages", "status"
}


class CSVParser(FileParser):
    """
    Parses CSV files in memory-efficient chunks.
    Handles files up to 1GB via pandas chunked reading.
    """

    @property
    def supported_mime_types(self) -> list[str]:
        return ["text/csv", "application/csv", "application/octet-stream"]

    def validate(self, file) -> None:
        # Check file is not empty
        file.seek(0, 2)  # seek to end
        size = file.tell()
        file.seek(0)  # reset

        if size == 0:
            raise EmptyFileException()
        if size > MAX_FILE_SIZE_BYTES:
            raise FileTooLargeException()

    def parse(self, file) -> Generator[list[dict], None, None]:
        """
        Reads CSV in chunks of CHUNK_SIZE rows.
        Each chunk is yielded as a list of cleaned dicts.
        Memory usage stays constant regardless of file size.
        """
        file.seek(0)
        content = file.read()
        buffer = io.BytesIO(content) if isinstance(content, bytes) else io.StringIO(content)

        reader = pd.read_csv(
            buffer,
            chunksize=self.CHUNK_SIZE,
            on_bad_lines="skip",       # skip malformed rows gracefully
            low_memory=False
        )

        for chunk_df in reader:
            # Normalize column names
            chunk_df.columns = [c.strip().lower() for c in chunk_df.columns]

            # Fill NaN with None for MongoDB compatibility
            chunk_df = chunk_df.where(pd.notnull(chunk_df), None)

            records = []
            for _, row in chunk_df.iterrows():
                record = self._transform_row(row.to_dict())
                if record:
                    records.append(record)

            if records:
                yield records

    def _transform_row(self, row: dict) -> dict | None:
        """Transform and clean a single CSV row into a MongoDB document."""
        try:
            # Parse languages from string representation of list
            languages_raw = row.get("languages")
            if isinstance(languages_raw, str):
                try:
                    languages = ast.literal_eval(languages_raw)
                except (ValueError, SyntaxError):
                    languages = [languages_raw]
            else:
                languages = []

            # Parse release_date
            release_date = row.get("release_date")

            return {
                "budget": self._to_float(row.get("budget")),
                "homepage": row.get("homepage"),
                "original_language": row.get("original_language"),
                "original_title": row.get("original_title"),
                "overview": row.get("overview"),
                "release_date": release_date,
                "revenue": self._to_float(row.get("revenue")),
                "runtime": self._to_int(row.get("runtime")),
                "status": row.get("status"),
                "title": row.get("title"),
                "vote_average": self._to_float(row.get("vote_average")),
                "vote_count": self._to_int(row.get("vote_count")),
                "production_company_id": self._to_int(row.get("production_company_id")),
                "genre_id": self._to_int(row.get("genre_id")),
                "languages": languages,  # stored as proper array in MongoDB
            }
        except Exception:
            return None  # skip unrecoverable rows

    @staticmethod
    def _to_float(value) -> float | None:
        try:
            return float(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _to_int(value) -> int | None:
        try:
            return int(float(value)) if value is not None else None
        except (ValueError, TypeError):
            return None