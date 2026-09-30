# Perfume Journal

Personal perfume collection tracker and journal.

The project currently provides the first in-memory API slice: creating perfume
records through FastAPI. Stored data is lost when the application restarts.

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

## Development checks

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy --strict .
uv lock --check
```
