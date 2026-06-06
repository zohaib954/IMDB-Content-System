# IMDB Content Upload & Review System

A backend system that lets a content team upload movie data via CSV and exposes APIs to query it — built as part of the DailyRounds SDE-1 take-home assignment.

**Live demo:** https://marrow.zohaibdev.com  
**Stack:** Python · Flask · MongoDB · Celery · Redis · Docker · GCP

---

## What it does

The content team uploads a CSV file (up to 1GB) containing movie data. The system parses it and stores it in MongoDB. A separate API lets you query the data with filtering, sorting, and pagination.

Two upload modes are supported:

- **Sync** — the request blocks until all records are inserted. Simple, measurable, not suitable for production at scale.
- **Async** — returns a `job_id` in ~50ms. A Celery worker processes the file in the background. You poll a status endpoint to track progress.

On the same 45,428-row CSV, sync took **190 seconds** end-to-end. Async returned to the client in **50ms** and finished processing in **99 seconds** — with Flask free to serve other requests the entire time.

---

## Project structure

```
imdb-content-system/
├── app/
│   ├── __init__.py              # App factory
│   ├── config.py                # Dev / Test / Prod config classes
│   ├── extensions.py            # MongoDB and Celery initialization
│   │
│   ├── ingestion/               # File parsing — pluggable by design
│   │   ├── base_parser.py       # Abstract FileParser interface
│   │   ├── csv_parser.py        # CSV implementation (chunked, 1GB safe)
│   │   └── parser_factory.py    # Picks parser by MIME type
│   │
│   ├── movies/
│   │   ├── repository.py        # All MongoDB queries live here
│   │   ├── service.py           # Business logic
│   │   ├── routes.py            # Flask blueprints — HTTP layer only
│   │   ├── schemas.py           # Request validation (marshmallow)
│   │   └── tasks.py             # Celery async task
│   │
│   ├── core/
│   │   ├── exceptions.py        # Custom exception hierarchy
│   │   └── responses.py         # Standardized API response format
│   │
│   └── templates/
│       └── index.html           # Minimal UI served by Flask
│
├── tests/
│   ├── conftest.py
│   ├── unit/                    # Parser and service tests (mongomock)
│   └── integration/             # API endpoint tests
│
├── postman/
│   └── IMDB_Content_System.postman_collection.json
│
├── Caddyfile                    # Reverse proxy + automatic HTTPS
├── docker-compose.yml           # Redis + Flask + Celery + Caddy
├── Dockerfile
├── celery_worker.py
└── run.py
```

---

## Design decisions

**Repository pattern** — all MongoDB queries are in `repository.py`. The service layer has no database imports. If you want to swap MongoDB for PostgreSQL, you change one file.

**Open/Closed principle (file ingestion)** — `FileParser` is an abstract class. Adding Excel or JSON support means creating one new file that extends `FileParser` and registering it in `ParserFactory`. Nothing else changes.

**Factory pattern** — `ParserFactory.get_parser(mime_type)` returns the right parser automatically. The route handler doesn't need to know which format it's dealing with.

**Chunked reading** — pandas reads the CSV in chunks of 1,000 rows. Memory usage stays constant regardless of file size. A 1GB file uses the same ~8MB RAM as a 1MB file.

**Two upload modes** — sync is useful for benchmarking and simple cases. Async is what you'd actually use in production. Both are first-class and properly documented.

---

## API reference

### Upload

```
POST /api/v1/movies/upload/sync
```
Multipart form, field name `file`. Blocks until processing completes. Returns total records inserted and time taken.

```
POST /api/v1/movies/upload/async
```
Same input. Returns immediately with a `job_id`. Processing happens in a Celery worker.

```
GET /api/v1/movies/upload/status/<job_id>
```
Poll this for async job progress. Status: `pending` → `processing` → `completed` / `failed`.

### Movies

```
GET /api/v1/movies/
```

Query parameters:

| Parameter | Type | Example | Notes |
|-----------|------|---------|-------|
| `year` | int | `?year=1995` | Filters by release year |
| `language` | string | `?language=English` | Partial match, OR logic for multi-language films |
| `sort_by` | string | `?sort_by=ratings_desc` | `release_date_asc`, `release_date_desc`, `ratings_asc`, `ratings_desc` |
| `page` | int | `?page=2` | Default: 1 |
| `page_size` | int | `?page_size=50` | Default: 20, max: 100 |

All responses follow this shape:

```json
{
  "success": true,
  "message": "Success",
  "data": [...],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 45428,
    "total_pages": 2272
  }
}
```

### Other

```
GET /health
```
Returns `{"status": "ok"}`. Used by the load balancer.

---

## Local setup

**Requirements:** Python 3.11+, Docker Desktop, a MongoDB Atlas account (free tier is fine).

```bash
# Clone
git clone https://github.com/zohaib954/IMDB-Content-System.git
cd IMDB-Content-System

# Virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# Dependencies
pip install -r requirements.txt

# Environment
cp .env.example .env
# Edit .env and fill in your MONGO_URI from MongoDB Atlas
```

**MongoDB Atlas setup (5 minutes):**

1. Go to cloud.mongodb.com → create a free M0 cluster
2. Database Access → add a user with a password (no special characters)
3. Network Access → Add IP → Allow Access From Anywhere (0.0.0.0/0)
4. Connect → Drivers → copy the connection string → add `/imdb_movies` before the `?`

Your `MONGO_URI` should look like:
```
mongodb+srv://user:password@cluster0.xxxxx.mongodb.net/imdb_movies?retryWrites=true&w=majority
```

**Start Redis:**

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

**Run the app (three terminals):**

```bash
# Terminal 1 — Flask
python run.py

# Terminal 2 — Celery worker
celery -A celery_worker.celery worker --loglevel=info --pool=solo   # Windows
celery -A celery_worker.celery worker --loglevel=info               # Mac/Linux
```

Open http://localhost:5000 — you'll land on the UI.

---

## Running with Docker

If you'd rather not set up Python locally:

```bash
cp .env.example .env
# Fill in MONGO_URI
# Change CELERY_BROKER_URL and CELERY_RESULT_BACKEND to redis://redis:6379/0

docker-compose up --build
```

All four services start automatically. The app is available at http://localhost.

---

## Tests

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=app --cov-report=term-missing
```

15 tests across unit and integration. Coverage: ~79%.

The tests use `mongomock` so you don't need a real MongoDB connection to run them.

**Test breakdown:**

- `test_csv_parser.py` — parser validates files, parses records correctly, handles malformed rows without crashing, returns languages as a list
- `test_movie_service.py` — sync upload inserts records and returns stats, pagination math is correct, year and language filters work
- `test_upload_api.py` — upload endpoint returns 201 on success, 400 with no file, 415 with wrong MIME type, list endpoint validates query params

---

## Postman collection

Import `postman/IMDB_Content_System.postman_collection.json` into Postman.

Set the `base_url` variable to `http://localhost:5000` (or `https://marrow.zohaibdev.com` for the live version).

The collection has 10 requests covering the full API surface — upload, status polling, listing with each filter and sort option individually, and a combined query.

---

## Deployment

The live version runs on a GCP e2-medium VM in Mumbai. Caddy handles HTTPS automatically via Let's Encrypt — no manual certificate management.

```
Client → Caddy (:443) → Flask (:5000)
                      → Celery worker
                      → Redis (internal)
```

The subdomain `marrow.zohaibdev.com` points to the GCP VM via an A record on Netlify DNS.

---

## CSV format

The system expects a CSV with these columns:

```
budget, homepage, original_language, original_title, overview,
release_date, revenue, runtime, status, title, vote_average,
vote_count, production_company_id, genre_id, languages
```

The `languages` column should contain a Python list representation: `['English', 'Français']`. The parser handles this automatically.

Malformed rows are skipped silently — the upload continues and reports how many records were actually inserted.
