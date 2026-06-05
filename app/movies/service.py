import time
import threading
from datetime import datetime

from app.ingestion.parser_factory import ParserFactory
from app.movies.repository import MovieRepository
from app.core.exceptions import UploadJobNotFoundException


class MovieService:
    """
    Service layer: orchestrates business logic.
    Never touches HTTP (Flask) or DB (MongoDB) directly.
    """

    def __init__(self, repository: MovieRepository, jobs_col):
        self._repo = repository
        self._jobs_col = jobs_col

    # -------------------------------------------------------------------------
    # SYNC upload (Version 1) - blocks until complete, returns timing
    # -------------------------------------------------------------------------

    def upload_sync(self, file, filename: str, mime_type: str) -> dict:
        """
        Synchronous upload: parse and insert in the same request.
        Returns performance stats for comparison with async version.
        """
        parser = ParserFactory.get_parser(mime_type)
        parser.validate(file)

        start_time = time.time()
        total_inserted = 0

        for chunk in parser.parse(file):
            total_inserted += self._repo.bulk_insert(chunk)

        elapsed = round(time.time() - start_time, 3)

        return {
            "mode": "sync",
            "filename": filename,
            "total_inserted": total_inserted,
            "processing_time_seconds": elapsed,
        }

    # -------------------------------------------------------------------------
    # ASYNC upload (Version 2) - returns job_id immediately, processes in bg
    # -------------------------------------------------------------------------

    def upload_async(self, file, filename: str, mime_type: str) -> dict:
        """
        Asynchronous upload via Celery task.
        Validates file immediately, then hands off to worker.
        Returns job_id for status polling.
        """
        parser = ParserFactory.get_parser(mime_type)
        parser.validate(file)

        # Read file content before handing to Celery (file object not serializable)
        file_content = file.read()

        job_id = self._repo.create_upload_job(self._jobs_col, filename)

        # Import here to avoid circular imports
        from app.movies.tasks import process_upload_task
        process_upload_task.delay(job_id, file_content, filename, mime_type)

        return {
            "mode": "async",
            "job_id": job_id,
            "filename": filename,
            "message": "Upload started. Poll /api/v1/movies/upload/status/{job_id} for progress.",
        }

    def get_job_status(self, job_id: str) -> dict:
        job = self._repo.get_upload_job(self._jobs_col, job_id)
        if not job:
            raise UploadJobNotFoundException(job_id)
        return job

    # -------------------------------------------------------------------------
    # Movie listing
    # -------------------------------------------------------------------------

    def list_movies(
        self,
        year: int | None,
        language: str | None,
        sort_by: str | None,
        page: int,
        page_size: int,
    ) -> dict:
        return self._repo.find_movies(
            year=year,
            language=language,
            sort_by=sort_by,
            page=page,
            page_size=page_size,
        )