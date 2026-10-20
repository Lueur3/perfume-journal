# Perfume Journal

Personal perfume collection tracker and journal.

The project currently provides in-memory API slices for creating perfume
records, adding physical samples or bottles to them, and recording wearings
for those collection items. A perfume can be retrieved with its collection
items, wearing history, and calculated average rating. Stored data is lost when
the application restarts.

## Requirements

- Python 3.14
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL 18 for database operations and integration tests

## Install

```powershell
uv sync
```

## Run

```powershell
uv run uvicorn perfume_journal.api:app --reload
```

Interactive API documentation is available at <http://127.0.0.1:8000/docs>, and
the OpenAPI schema is available at <http://127.0.0.1:8000/openapi.json>.

## PostgreSQL setup and migrations

SQLAlchemy ORM models and the initial Alembic migration describe the
`perfumes`, `collection_items`, and `wearings` tables. The API still uses
in-memory storage; creating these tables does not switch its storage backend.

Create an empty PostgreSQL database named `perfume_journal`. Copy
`.env.example` to `.env` in the project root and fill in your local connection
parameters, including the PostgreSQL role and password. Keep `.env` private;
only the template belongs in Git.

The shared configuration function loads `.env` with python-dotenv. Existing
environment variables take precedence over values in the file. No
`--env-file` argument or repeated PowerShell assignments are needed.

Check the connection:

```powershell
uv run python -m perfume_journal.db_check
```

The diagnostic uses an async session to run `SELECT current_database()`.
The expected output is `perfume_journal`. Keep passwords out of source files
and command output.

Apply the checked-in migrations and inspect the current database revision:

```powershell
uv run alembic upgrade head
uv run alembic current
```

The initial revision is `25bdb52d3933`. It creates the three domain tables;
Alembic tracks the applied revision in its own `alembic_version` table.
Migration files live in `migrations/versions`. Review generated migrations
before applying them. Downgrading the initial migration drops the three domain
tables and their data.

### PostgreSQL storage operations

`perfume_journal.sqlalchemy_store.create_perfume()` creates a perfume through
an async session factory and returns its Pydantic representation after a
successful commit. Both storage implementations use the same normalization
function for duplicate detection keys.

Only a unique violation (`23505`) of `uq_brand_name_concentration_keys` is
translated into `DuplicatePerfumeError`. Other integrity errors propagate
without that translation.

`perfume_journal.sqlalchemy_store.get_perfume()` opens a session and retrieves
one perfume by its primary key. It returns a Pydantic `Perfume` containing
`id`, `brand`, `name`, and `concentration`, or raises the shared
`PerfumeNotFoundError` if the record does not exist. It does not assemble
collection items or wearings.

`perfume_journal.sqlalchemy_store.create_collection_item()` checks that the
parent perfume exists and inserts a physical sample or bottle in the same
session and transaction. A missing parent raises `PerfumeNotFoundError`.
PostgreSQL assigns the item ID and the default `active` status. The operation
returns a Pydantic `CollectionItem` after a successful commit. Volume and
acquisition date may be omitted, and identical items are allowed as separate
physical instances.

`perfume_journal.sqlalchemy_store.create_wearing()` checks that the parent
collection item exists and inserts a wearing in the same session and
transaction. A missing parent raises the shared `CollectionItemNotFoundError`.
It returns a Pydantic `Wearing` after a successful commit. The supplied wearing
time is preserved as an instant; rating and comment may be omitted. Repeated
wearings with identical data are allowed and receive separate IDs.

These operations are not yet connected to the HTTP API. The existing GET
endpoint still returns `PerfumeDetails` from in-memory storage.

## API

### `POST /perfumes`

Creates a perfume record. `brand` and `name` are required;
`concentration` is optional. The server assigns the `id`.

Example request:

```json
{
  "brand": "Creed",
  "name": "Aventus",
  "concentration": "EDP"
}
```

Responses:

- `201 Created` — the perfume was created;
- `409 Conflict` — a perfume with the same normalized brand, name, and
  concentration already exists;
- `422 Unprocessable Content` — the request body is invalid.

### `POST /perfumes/{perfume_id}/collection-items`

Adds one physical sample or bottle to an existing perfume record. New
collection items are created with the `active` status. The server assigns the
item `id` and takes `perfume_id` from the URL.

Example request:

```json
{
  "kind": "sample",
  "initial_volume_ml": 1.5,
  "acquired_on": "2026-05-09"
}
```

Responses:

- `201 Created` — the collection item was created;
- `404 Not Found` — the referenced perfume does not exist;
- `422 Unprocessable Content` — the request body is invalid.

### `POST /collection-items/{collection_item_id}/wearings`

Records one wearing of an existing collection item. `worn_at` is required and
must include a timezone offset. `rating` is an optional integer from 1 to 10,
and `comment` is optional. The server assigns the wearing `id` and takes
`collection_item_id` from the URL.

Example request:

```json
{
  "worn_at": "2026-10-02T09:30:00+03:00",
  "rating": 5,
  "comment": "Test comment"
}
```

Responses:

- `201 Created` — the wearing was created;
- `404 Not Found` — the referenced collection item does not exist;
- `422 Unprocessable Content` — the request body is invalid.

### `GET /perfumes/{perfume_id}`

Returns a perfume together with its collection items, each item's wearing
history, and the average of all specified wearing ratings. Wearings without a
rating remain in the history but do not affect the average. `average_rating` is
`null` when no wearing has a rating.

Responses:

- `200 OK` — the assembled perfume details were returned;
- `404 Not Found` — the referenced perfume does not exist.

## Database tests

The full test suite requires a running PostgreSQL server and a separate,
migrated test database. Create an empty database named `perfume_journal_test`
on the same server, accessible by the role configured in `.env`. Set:

```dotenv
PERFUME_TEST_DB_NAME=perfume_journal_test
```

Keep `PERFUME_DB_NAME` pointed at the development database. An empty test
database name or one equal to the development database name is rejected.

Apply the existing migrations to the test database:

```powershell
uv run alembic -x environment=test upgrade head
uv run alembic -x environment=test current
```

Without `-x environment=test`, Alembic continues to use the development
database. Unknown `environment` values are rejected.

Database tests use AnyIO with the asyncio backend. For each store test, the
session factory is bound to one connection inside an external transaction,
with sessions using savepoints. The external transaction is rolled back after
the test, including changes committed by the operation under test. PostgreSQL
sequence values are not reset by this rollback.

Run just the database tests:

```powershell
uv run pytest tests/test_sqlalchemy_store.py -q
```

## Development checks

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy --strict .
uv lock --check
```
