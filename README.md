# Media Monitoring API

## How to Run

### 1. Clone

```bash
git clone https://github.com/Taqiy-Code/TestAssessmentPeopleAndPixel.git
cd TestAssessmentPeopleAndPixel
```

### 2. Environment

```bash
cp .env.example .env
```

Edit `.env` and set your PostgreSQL connection string:

```env
DATABASE_URL=postgresql://user:password@host:port/dbname
```

### 3. Install Dependencies

```bash
pip install uv
uv sync
```

### 4. Database Setup

Apply all migration files to set up the schema and indexes:

```bash
psql $DATABASE_URL -f migrations/001_init.sql
psql $DATABASE_URL -f migrations/002_add_unique_to_mentions.sql
```

### 5. Run

```bash
uv run python -m app.main
```

API available at: `http://127.0.0.1:8000`
Swagger docs: `http://127.0.0.1:8000/docs`

### 6. Test the Endpoint

Seed sample data:

```bash
curl -X POST http://127.0.0.1:8000/internal/mentions/bulk \
  -F "file=@seed_mentions.json"
```

Query mentions:

```bash
curl "http://127.0.0.1:8000/mentions?source=twitter&page=1&page_size=10"
```

---

## Schema

```sql
CREATE TABLE mentions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  external_id     TEXT NOT NULL,
  source          TEXT NOT NULL,
  title           TEXT,
  content         TEXT NOT NULL,
  url             TEXT NOT NULL UNIQUE,
  author          TEXT,
  published_at    TIMESTAMPTZ,
  engagement      INT,
  idempotency_key TEXT NOT NULL UNIQUE,
  created_at      TIMESTAMPTZ DEFAULT now()
);
```

**Why modelled this way:**

- `id` is a UUID generated server-side so ingestion from multiple sources never collides on primary key.
- `url` has a `UNIQUE` constraint to prevent identical links from being duplicated.
- `published_at` is `TIMESTAMPTZ` (timezone-aware) because sources publish from different timezones. Storing naive datetimes would make date-range filtering unreliable.
- `engagement` is stored as `INT` after normalization — the raw input can be a float, a comma-formatted string (`"1,200"`), or a boolean, all coerced at ingest time.
- `idempotency_key` is a computed SHA-256 hash field derived from `title` and `content` with a `UNIQUE` constraint, used as the deduplication handle.
- Indexes on `source` and `published_at` directly support the two most common filter patterns in `GET /mentions`.

---

## Duplicate Detection & Upsert Strategy

**Rule 1 (URL Collision):** Handled via a Writable CTE. If a URL already exists in the database, the system performs an `UPDATE` to backfill any `NULL` fields using `COALESCE`, and applies `GREATEST` for the engagement score. The insertion step is subsequently skipped.

**Rule 2 (Idempotency Key Collision):** 
`idempotency_key = sha256(f"{title}|{content}")`

If the URL is new but the hashed content + title is identical to an existing record, the system relies on Postgres' `ON CONFLICT (idempotency_key) DO UPDATE SET ...` to similarly merge the incoming data, backfilling missing attributes.

**Why:** Using a dual-collision strategy ensures that we capture both cross-platform identical URLs and cross-URL identical contents without creating spam records, whilst actively maintaining the most complete version of the data (coalescing nulls).

---

## Assumptions

- **Date ambiguity:** Date formats in the input are inconsistent. Unambiguous formats are successfully parsed. However, slash-based formats (like `10/08/2026`) that cannot be definitively identified as `DD/MM/YYYY` or `MM/DD/YYYY` are explicitly rejected to prevent silent data corruption.
- `engagement` values may arrive as strings like `"1,200"` or `"150.0"`. These are normalised to `int` at ingest time.
- `title` and `content` may contain raw HTML from scraped sources. These are stripped with BeautifulSoup before storage.
- The `/internal/mentions/bulk` endpoint is internal-only and does not require authentication in this scope.

---

## Trade-offs

**Per-record error handling in bulk ingest** — A single malformed record (like an ambiguous date) does not abort the entire batch. Invalid records are collected and reported as `not_processed` in the JSON response but otherwise discarded. This was chosen because real-world feed data is frequently dirty.

**`ORDER BY published_at DESC, id DESC`** — `published_at` alone is not sufficient for stable pagination because multiple records can share the same timestamp. Adding `id DESC` as a tie-breaker guarantees a consistent row order across pages.

---

## Time Spent

Around **7-8 hours** across multiple sessions (core implementation, schema refinement, duplicate detection hardening, and testing).

---

## With Another Week, I Would...

1. **Structured logging** — Replace bare `print(e)` with `structlog` or Python's `logging` module for production-grade observability.
2. **CI pipeline** — Add a GitHub Actions workflow that runs `pytest` on every pull request.
3. **Service Layer Refactoring** - Move business logic (DB queries, data normalization) completely out of the routers into dedicated service classes.
