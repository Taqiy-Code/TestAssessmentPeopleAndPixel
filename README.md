# Media Monitoring API

A asynchronous REST backend for ingesting, normalizing, deduplicating, querying, and charting media mentions.

---

## 1. Tech Stack

- **Python 3.12**: Modern Python runtime with strong typing support.
- **FastAPI**: Asynchronous web framework chosen for high throughput, automatic OpenAPI (Swagger) documentation, and native Pydantic v2 validation.
- **Pydantic (v2)**: Strict data contract validation for both incoming requests and outgoing structured responses.
- **PostgreSQL**: Robust relational database offering native JSON support, ACID guarantees, and advanced indexing capabilities.
- **asyncpg**: High-performance, asynchronous PostgreSQL client communicating directly over PostgreSQL binary protocol without ORM overhead.
- **BeautifulSoup4**: HTML parser for sanitizing rich text and stripping markup from scraped content.
- **uv**: Blazing-fast Python package resolver and environment manager.
- **Docker & Docker Compose**: Automated containerized environment ensuring reproducible execution across machines.
- **pytest**: Test runner for unit and endpoint integration testing.

---

## 2. Project Structure

```text
.
├── app/
│   ├── main.py        # Application initialization, lifespan DB connection pool, global exception handlers
│   ├── routers.py     # HTTP routes for bulk ingest, search, and metrics aggregation
│   ├── schemas.py     # Pydantic models for request filters, pagination, and response payloads
│   ├── utils.py       # Data cleaners (HTML sanitizer, date parser, int parser, source normalizer)
│   └── db.py          # Database pool factory using asyncpg
├── migrations/        # Sequential SQL migration files
│   ├── 001_init.sql                 # Base table creation with source & published_at indexes
│   ├── 002_add_unique_to_mentions.sql # Unique index for URL deduplication
│   └── 003_reindex_mentions.sql       # Reindex script for mitigating MVCC dead tuple bloat
├── tests.py           # Pytest test suite covering edge cases and risky logic
├── Dockerfile         # Multi-stage/isolated container definition with uv virtual environment
├── docker-compose.yml # Orchestrates PostgreSQL service (with auto-migrations) & FastAPI backend
├── pyproject.toml     # Project metadata and locked dependency specifications
├── requirements.txt   # Standard pip requirements snapshot
├── seed_mentions.json # Raw sample dataset representing messy real-world feeds
└── README.md          # Comprehensive project documentation
```

---

## 3. How to Run

### Option A: Run with Docker Compose (Recommended)

The Docker Compose configuration spins up PostgreSQL 15 and the FastAPI app. SQL migrations inside `migrations/` are automatically mounted and executed when the database initializes.

```bash
# 1. Clone repository
git clone https://github.com/Taqiy-Code/TestAssessmentPeopleAndPixel.git
cd TestAssessmentPeopleAndPixel

# 2. Build and start services
docker-compose up --build -d
```

- **API Base URL**: `http://localhost:8000`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`

---

### Option B: Run Locally without Docker

If you prefer to run natively on your machine:

#### 1. Prerequisites
- Python 3.12+
- PostgreSQL server running locally or remotely
- `uv` package manager (`pip install uv`)

#### 2. Environment Setup
```bash
cp .env.example .env
```
Edit `.env` and set your PostgreSQL connection string:
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/mentions_db
```

#### 3. Install Dependencies
```bash
uv sync
```

#### 4. Apply Database Migrations
Execute the migrations in order using `psql`:
```bash
psql $DATABASE_URL -f migrations/001_init.sql
psql $DATABASE_URL -f migrations/002_add_unique_to_mentions.sql
```

#### 5. Start the Application
```bash
uv run python -m app.main
```

---

### 4. Running Tests

Run the complete test suite using pytest:
```bash
uv run pytest tests.py -v
```

---

## 4. API Documentation & Endpoints

### 1. Bulk Ingest Mentions
- **Endpoint**: `POST /internal/mentions/bulk`
- **Content-Type**: `multipart/form-data`
- **Description**: Accepts a JSON file upload containing an array of raw mention items. Cleanses, normalizes, deduplicates, and upserts valid records. Returns lists and counts for both processed and rejected items.

**Sample Request**:
```bash
curl -X POST http://127.0.0.1:8000/internal/mentions/bulk \
  -F "file=@seed_mentions.json"
```

**Sample Response (`200 OK`)**:
```json
{
  "data": {
    "processed": {
      "count": 12,
      "data": [
        {
          "external_id": "post_101",
          "source": "Twitter",
          "title": "Tech Launch 2026",
          "content": "Exciting announcement today regarding our new AI platform.",
          "url": "https://twitter.com/news/101",
          "author": "john_doe",
          "published_at": "2026-08-10T08:15:00Z",
          "engagement": 1250
        }
      ]
    },
    "not_processed": {
      "count": 1,
      "data": [
        {
          "external_id": "bad_item",
          "source": "Blog",
          "content": "Missing required fields..."
        }
      ]
    }
  }
}
```

---

### 2. Search Mentions
- **Endpoint**: `GET /mentions`
- **Query Parameters**:
  - `q` (string, optional): Case-insensitive keyword search across `title` and `content`.
  - `source` (string, optional): Exact filter by mention source name.
  - `from` (ISO datetime string, optional): Earliest publication date (`published_at >= from`).
  - `to` (ISO datetime string, optional): Latest publication date (`published_at <= to`).
  - `page` (integer, default: 1, min: 1): Page number.
  - `page_size` (integer, default: 10, min: 1): Number of items per page.

**Sample Request**:
```bash
curl "http://127.0.0.1:8000/mentions?q=tech&source=Twitter&page=1&page_size=10"
```

**Sample Response (`200 OK`)**:
```json
{
  "page": 1,
  "page_size": 10,
  "total_items": 45,
  "total_pages": 5,
  "has_next": true,
  "has_prev": false,
  "data": [
    {
      "external_id": "post_101",
      "source": "Twitter",
      "title": "Tech Launch 2026",
      "content": "Exciting announcement today...",
      "url": "https://twitter.com/news/101",
      "author": "john_doe",
      "published_at": "2026-08-10T08:15:00Z",
      "engagement": 1250
    }
  ]
}
```

---

### 3. Aggregated Mentions Stats
- **Endpoint**: `GET /mentions/stats`
- **Query Parameters**:
  - `group_by` (string, required): Either `"source"` or `"day"`.

**Sample Request (By Source)**:
```bash
curl "http://127.0.0.1:8000/mentions/stats?group_by=source"
```
**Sample Response**:
```json
[
  { "data": "Twitter", "count": 120, "type": "source" },
  { "data": "NewsAPI", "count": 45, "type": "source" }
]
```

**Sample Request (By Day)**:
```bash
curl "http://127.0.0.1:8000/mentions/stats?group_by=day"
```
**Sample Response**:
```json
[
  { "data": "2026-08-10T00:00:00Z", "count": 65, "type": "day" },
  { "data": "2026-08-09T00:00:00Z", "count": 40, "type": "day" }
]
```

---

## 5. Schema & Data Model

```sql
CREATE TABLE mentions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  external_id     TEXT NOT NULL,
  source          TEXT NOT NULL,
  title           TEXT,
  content         TEXT NOT NULL,
  url             TEXT NOT NULL,
  author          TEXT,
  published_at    TIMESTAMPTZ,
  engagement      INT,
  idempotency_key TEXT NOT NULL UNIQUE,
  created_at      TIMESTAMPTZ DEFAULT now()
);

-- Indexes for search and aggregation performance
CREATE INDEX idx_mentions_source ON mentions (source);
CREATE INDEX idx_mentions_published_at ON mentions (published_at);
CREATE UNIQUE INDEX idx_mentions_url ON mentions (url);
```

### Why Modelled This Way:
1. **UUID Primary Key (`id`)**: Server-generated UUID prevents primary key collisions across multi-source concurrent ingestions.
2. **`external_id` as regular column**: Upstream IDs are not globally unique across different third-party platforms (e.g., ID `1001` might exist on both Twitter and Reddit).
3. **`TIMESTAMPTZ` for `published_at`**: Stores UTC-normalized timestamps with offset awareness, preventing timezone drift and ensuring consistent date-range queries (`from`/`to`).
4. **`INT` for `engagement`**: Standardizes diverse inputs (floats, comma strings, booleans) into a clean integer metric suitable for sorting and analytics.
5. **`idempotency_key`**: SHA-256 hash of normalized `title` and `content` with a unique index, ensuring cross-platform identical articles are detected even if posted under different IDs.
6. **Dedicated Indexes**:
   - `idx_mentions_source`: Eliminates table scans for source filtering and source aggregation (`GROUP BY source`).
   - `idx_mentions_published_at`: Supports fast range filtering and indexed pagination sorting.
   - `idx_mentions_url`: Enforces link uniqueness and speeds up CTE update queries.

---

## 6. Data Cleaning & Normalization Pipeline

During ingestion, each raw item is sanitized through `app/utils.py`:
1. **HTML Stripping**: `normalize_text()` parses `title` and `content` with BeautifulSoup to strip HTML tags (e.g., `<p>`, `<b>`, `&amp;`), extracting clean plain text.
2. **Source Normalization**: `normalize_source()` strips irregular leading/trailing whitespaces and collapses multi-spaces.
3. **Engagement Numeric Coercion**: `parse_int()` converts comma-separated strings (`"1,200"` -> `1200`), floats (`10.5` -> `10`), booleans (`True` -> `1`), and strips whitespace.
4. **Date Parsing & UTC Normalization**:
   - Unix epoch timestamps (seconds/floats) -> converted to UTC datetime.
   - ISO 8601 strings (e.g., `2026-08-10T08:15:00Z` or with offsets `+08:00`) -> parsed into timezone-aware datetimes.
   - Custom dates without timestamps -> parsed and explicitly tagged with `timezone.utc`.
   - Native datetime objects -> safely preserved with UTC fallback.

---

## 7. Duplicate Detection 

The system enforces a dual-layered duplicate detection mechanism:

```sql
WITH url_update AS (
    UPDATE mentions 
    SET engagement = GREATEST(mentions.engagement, $8),
        title = COALESCE(mentions.title, $3),
        content = COALESCE(mentions.content, $4),
        author = COALESCE(mentions.author, $6),
        published_at = COALESCE(mentions.published_at, $7)
    WHERE url = $5
    RETURNING id
)
INSERT INTO mentions (external_id, source, title, content, url, author, published_at, engagement, idempotency_key)
SELECT $1, $2, $3, $4, $5, $6, $7, $8, $9
WHERE NOT EXISTS (SELECT 1 FROM url_update)
ON CONFLICT (idempotency_key) DO UPDATE SET 
    engagement = GREATEST(mentions.engagement, EXCLUDED.engagement), 
    title = COALESCE(mentions.title, EXCLUDED.title), 
    content = COALESCE(mentions.content, EXCLUDED.content),
    url = COALESCE(mentions.url, EXCLUDED.url),
    author = COALESCE(mentions.author, EXCLUDED.author),
    published_at = COALESCE(mentions.published_at, EXCLUDED.published_at);
```

### Rule Explanation:
1. **Rule 1 (URL Collision via Writable CTE)**: If a mention with the same canonical `url` already exists, we do not insert a duplicate row. Instead, we update the existing row by backfilling any previously `NULL` fields using `COALESCE` and taking the highest metric via `GREATEST(engagement, new_engagement)`.
2. **Rule 2 (Content Duplication via `idempotency_key`)**: If the URL is new but the content + title is identical (`idempotency_key = sha256(title|content)`), Postgres resolves the conflict via `ON CONFLICT (idempotency_key) DO UPDATE`.
3. **Data Completeness**: Combining `COALESCE` and `GREATEST` ensures subsequent scrapes enrich incomplete mentions rather than creating fragmented duplicates.

---

## 8. Assumptions Made

1. **Date Ambiguity Guard**: Date formats like `10/08/2026` are ambiguous (could be 10th August or 8th October). Rather than silently guessing and risking data corruption, the parser evaluates whether day > 12 (unambiguous `DD/MM/YYYY`) or month > 12 (unambiguous `MM/DD/YYYY`). If both numbers are $\le 12$, the parser explicitly raises a validation error and places the record in `not_processed`.
2. **Internal Ingest Scope**: `/internal/mentions/bulk` is designed as an internal pipeline receiver; auth/rate-limiting is omitted per brief specifications.
3. **Keyword Search Scope**: `q` operates across both `title` and `content` using case-insensitive substring matching.
4. **Stable Pagination Tie-Breaking**: Sorting solely on `published_at DESC` can cause pagination jitter when multiple records share identical timestamps. `ORDER BY published_at DESC NULLS LAST, id DESC` was adopted to guarantee a deterministic row sequence across all pages.

---

## 9. Trade-offs Accepted

1. **Raw SQL (`asyncpg`) over ORM**:
   - *Advantage*: Zero overhead, direct access to Postgres features (Writable CTEs, `ON CONFLICT`, `GREATEST`, `COALESCE`), and explicit transparent schema.
   - *Trade-off*: Queries are handwritten and mapped manually to Pydantic schemas.
2. **Synchronous Request Processing**:
   - *Advantage*: Immediate feedback to the caller on processed vs unprocessable counts.
   - *Trade-off*: Ingestion of multi-megabyte files may take several seconds under heavy load.
3. **Per-Record Error Isolation**:
   - *Advantage*: A single corrupted record in a batch of 1,000 does not roll back the 999 valid items.
   - *Trade-off*: Caller must inspect the `not_processed` array in the response to identify individual item failures.

---

## 10. Testing Strategy

The test suite in `tests.py` covers high-risk logic and regression points:
- **Date Parser Variations**: Unix timestamps, ISO 8601 offsets, zero-padded dates, unambiguous slash formats, and explicit rejection of ambiguous dates.
- **Data Normalizers**: Handling floats, commas, strings, and booleans in engagement numbers; HTML stripping from content.
- **Filter Date Validation**: Ensuring `from > to` triggers a 422 validation response.
- **Bulk Ingestion Fault Tolerance**: Empty payloads (`[]`), malformed JSON, and non-JSON file uploads.
- **Application Lifespan Context**: TestClient configured with lifespan context manager to verify connection pool creation and closure.

---

## 11. Time Spent

- **Total Time**: ~16 hours across 3 focused sessions.
  - *Session 1 (~5 hours)*: Architecture setup, FastAPI + asyncpg skeleton, initial schema migrations, normalization functions.
  - *Session 2 (~8 hours)*: Search filtering, stable pagination, CTE-based upsert deduplication, and stats endpoints.
  - *Session 3 (~3 hours)*: Strict Pydantic response models, Dockerization, comprehensive test coverage, and documentation.

---

## 12. With Another Week, I Would...

1. **Background Job Queue**: Offload `/internal/mentions/bulk` to an asynchronous task worker (e.g., Celery / ARQ with Redis) returning `202 Accepted` with a tracking task ID for massive feed uploads.
2. **Structured JSON Logging & Metrics**: Introduce `structlog` and OpenTelemetry middleware to trace request latencies and database query durations.
