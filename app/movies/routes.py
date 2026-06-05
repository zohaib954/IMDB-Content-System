from flask import Blueprint, request
from marshmallow import ValidationError

from app.extensions import mongo
from app.movies.repository import MovieRepository
from app.movies.service import MovieService
from app.movies.schemas import MovieListQuerySchema
from app.core.responses import success_response, error_response
from app.core.exceptions import AppException
from flask import Blueprint, request, render_template

movies_bp = Blueprint("movies", __name__, url_prefix="/api/v1/movies")

query_schema = MovieListQuerySchema()

@movies_bp.route("/ui")
def ui():
    return render_template("index.html")

def _get_service() -> MovieService:
    """Dependency injection: build service with its dependencies."""
    db = mongo.db
    repo = MovieRepository(db["movies"])
    return MovieService(repo, db["upload_jobs"])


# ---------------------------------------------------------------------------
# Upload endpoints
# ---------------------------------------------------------------------------

@movies_bp.route("/upload/sync", methods=["POST"])
def upload_sync():
    """
    POST /api/v1/movies/upload/sync
    Synchronous CSV upload. Blocks until processing complete.
    Use for benchmarking against async version.
    """
    if "file" not in request.files:
        return error_response("No file part in request.", 400)

    file = request.files["file"]
    if file.filename == "":
        return error_response("No file selected.", 400)

    mime_type = file.content_type or "application/octet-stream"

    try:
        service = _get_service()
        result = service.upload_sync(file, file.filename, mime_type)
        return success_response(
            data=result,
            message=f"Upload complete. {result['total_inserted']} records inserted.",
            status_code=201,
        )
    except AppException as e:
        return error_response(e.message, e.status_code)
    except Exception as e:
        return error_response(f"Unexpected error: {str(e)}", 500)


@movies_bp.route("/upload/async", methods=["POST"])
def upload_async():
    """
    POST /api/v1/movies/upload/async
    Asynchronous CSV upload via Celery. Returns immediately with job_id.
    Poll /upload/status/<job_id> for progress.
    """
    if "file" not in request.files:
        return error_response("No file part in request.", 400)

    file = request.files["file"]
    if file.filename == "":
        return error_response("No file selected.", 400)

    mime_type = file.content_type or "application/octet-stream"

    try:
        service = _get_service()
        result = service.upload_async(file, file.filename, mime_type)
        return success_response(
            data=result,
            message="Upload job queued successfully.",
            status_code=202,
        )
    except AppException as e:
        return error_response(e.message, e.status_code)
    except Exception as e:
        return error_response(f"Unexpected error: {str(e)}", 500)


@movies_bp.route("/upload/status/<job_id>", methods=["GET"])
def upload_status(job_id: str):
    """
    GET /api/v1/movies/upload/status/<job_id>
    Poll status of an async upload job.
    """
    try:
        service = _get_service()
        job = service.get_job_status(job_id)
        return success_response(data=job)
    except AppException as e:
        return error_response(e.message, e.status_code)


# ---------------------------------------------------------------------------
# Movie listing endpoint
# ---------------------------------------------------------------------------

@movies_bp.route("/", methods=["GET"])
def list_movies():
    """
    GET /api/v1/movies/
    Query params:
      - page (int, default=1)
      - page_size (int, default=20, max=100)
      - year (int, optional) — filter by release year
      - language (str, optional) — filter by language (partial match, OR logic)
      - sort_by (str, optional) — release_date_asc | release_date_desc |
                                   ratings_asc | ratings_desc
    """
    try:
        params = query_schema.load(request.args)
    except ValidationError as e:
        return error_response("Invalid query parameters.", 400, errors=e.messages)

    try:
        service = _get_service()
        result = service.list_movies(
            year=params.get("year"),
            language=params.get("language"),
            sort_by=params.get("sort_by"),
            page=params["page"],
            page_size=params["page_size"],
        )
        return success_response(
            data=result["items"],
            meta={
                "page": result["page"],
                "page_size": result["page_size"],
                "total": result["total"],
                "total_pages": result["total_pages"],
            },
        )
    except AppException as e:
        return error_response(e.message, e.status_code)
    except Exception as e:
        return error_response(f"Unexpected error: {str(e)}", 500)
    

@movies_bp.route("/debug/db", methods=["GET"])
def debug_db():
    try:
        db = mongo.db
        if db is None:
            return {"status": "ERROR", "reason": "mongo.db is None"}, 500
        collections = db.list_collection_names()
        return {"status": "OK", "collections": collections}, 200
    except Exception as e:
        return {"status": "ERROR", "reason": str(e)}, 500