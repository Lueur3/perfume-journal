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

## PostgreSQL connection check

The diagnostic module uses SQLAlchemy's async engine and asyncpg to run
`SELECT current_database()`. The API still uses in-memory storage.

Create an empty PostgreSQL database named `perfume_journal`, then set the
connection parameters in PowerShell 7. Use your server's host and port and
enter your PostgreSQL role and password when prompted:

```powershell
$env:PERFUME_DB_HOST = "127.0.0.1"
$env:PERFUME_DB_PORT = "5432"
$env:PERFUME_DB_NAME = "perfume_journal"
$env:PERFUME_DB_USER = Read-Host "PostgreSQL role"
$env:PERFUME_DB_PASSWORD = Read-Host "PostgreSQL password" -MaskInput
uv run python -m perfume_journal.db_check
```

The expected output is `perfume_journal`. Set the variables and run the command
in the same terminal session. The module reads environment variables directly;
it does not automatically load a `.env` file. Keep passwords out of source files
and command output.

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

## Development checks

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy --strict .
uv lock --check
```
