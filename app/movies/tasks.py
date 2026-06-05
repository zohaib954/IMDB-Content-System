import io
import time
from datetime import datetime

from app.extensions import celery, mongo
from app.movies.repository import MovieRepository
from app.ingestion.csv_parser import CSVParser
from app.ingestion.parser_factory import ParserFactory


@celery.task(bind=True, name="movies.process_upload")
def process_upload_task(self, job_id: str, file_content: bytes, filename: str, mime_type: str):
    """
    Celery task: processes CSV upload in background worker.
    Updates job status in MongoDB throughout processing.
    """
    db = mongo.db
    jobs_col = db["upload_jobs"]
    movies_col = db["movies"]
    repo = MovieRepository(movies_col)

    repo.update_upload_job(jobs_col, job_id, status="processing")

    start_time = time.time()
    total_inserted = 0

    try:
        parser = ParserFactory.get_parser(mime_type)
        file_obj = io.BytesIO(file_content)

        for chunk in parser.parse(file_obj):
            total_inserted += repo.bulk_insert(chunk)

        elapsed = round(time.time() - start_time, 3)

        repo.update_upload_job(
            jobs_col,
            job_id,
            status="completed",
            total_inserted=total_inserted,
            processing_time_seconds=elapsed,
            completed_at=datetime.utcnow().isoformat(),
        )

    except Exception as exc:
        repo.update_upload_job(
            jobs_col,
            job_id,
            status="failed",
            error=str(exc),
            completed_at=datetime.utcnow().isoformat(),
        )
        raise self.retry(exc=exc, countdown=0, max_retries=0)