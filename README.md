# Perfume Journal

Personal perfume collection tracker and journal.

The project currently provides a minimal FastAPI application shell. Domain endpoints and data storage have not been implemented yet.

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

The OpenAPI schema is available at <http://127.0.0.1:8000/openapi.json>. At the current stage, its `paths` object is empty because the application has no endpoints.

## Development checks

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy --strict .
uv lock --check
```
