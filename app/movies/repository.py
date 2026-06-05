from datetime import datetime
from pymongo.collection import Collection
from pymongo import ASCENDING, DESCENDING


SORT_MAP = {
    "release_date_asc": ("release_date", ASCENDING),
    "release_date_desc": ("release_date", DESCENDING),
    "ratings_asc": ("vote_average", ASCENDING),
    "ratings_desc": ("vote_average", DESCENDING),
}


class MovieRepository:
    """
    Repository Pattern: All MongoDB interactions live here.
    The service layer never touches the DB directly.
    Swap MongoDB for any other DB by replacing this class only.
    """

    def __init__(self, collection: Collection):
        self._col = collection

    def ensure_indexes(self):
        """Create indexes for filter and sort fields. Call once at startup."""
        self._col.create_index("languages")
        self._col.create_index("release_date")
        self._col.create_index("vote_average")
        self._col.create_index([("release_date", ASCENDING)])
        self._col.create_index([("vote_average", ASCENDING)])

    def bulk_insert(self, records: list[dict]) -> int:
        """Insert a batch of records. Returns count inserted."""
        if not records:
            return 0
        result = self._col.insert_many(records, ordered=False)
        return len(result.inserted_ids)

    def find_movies(
        self,
        year: int | None = None,
        language: str | None = None,
        sort_by: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """
        Paginated movie listing with optional filters and sorting.
        Returns dict with items, total, page, page_size, total_pages.
        """
        query = self._build_query(year, language)
        sort = self._build_sort(sort_by)

        total = self._col.count_documents(query)
        skip = (page - 1) * page_size

        cursor = self._col.find(query, {"_id": 0})

        if sort:
            cursor = cursor.sort(*sort)

        items = list(cursor.skip(skip).limit(page_size))

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, -(-total // page_size)),  # ceiling division
        }

    def _build_query(self, year: int | None, language: str | None) -> dict:
        query = {}

        if year:
            # Filter by year extracted from release_date string "YYYY-MM-DD"
            query["release_date"] = {
                "$regex": f"^{year}-",
                "$options": "i"
            }

        if language:
            # OR match: language appears anywhere in the languages array
            query["languages"] = {
                "$elemMatch": {"$regex": language, "$options": "i"}
            }

        return query

    def _build_sort(self, sort_by: str | None):
        if sort_by and sort_by in SORT_MAP:
            return SORT_MAP[sort_by]
        return None

    # --- Upload Job tracking ---

    def create_upload_job(self, jobs_col: Collection, filename: str) -> str:
        doc = {
            "filename": filename,
            "status": "pending",
            "total_inserted": 0,
            "error": None,
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": None,
        }
        result = jobs_col.insert_one(doc)
        return str(result.inserted_id)

    def update_upload_job(self, jobs_col: Collection, job_id: str, **kwargs):
        from bson import ObjectId
        jobs_col.update_one(
            {"_id": ObjectId(job_id)},
            {"$set": kwargs}
        )

    def get_upload_job(self, jobs_col: Collection, job_id: str) -> dict | None:
        from bson import ObjectId
        doc = jobs_col.find_one({"_id": ObjectId(job_id)}, {"_id": 0})
        return doc