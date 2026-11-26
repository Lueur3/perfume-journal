# Perfume Journal

A personal perfume collection and wearing journal, currently available through
an HTTP API with interactive Swagger documentation.

A **perfume** describes a fragrance. A **collection item** is a physical sample
or bottle of that perfume. A **wearing** records when an item was worn, with an
optional rating and comment.

- Create, view, edit, and delete perfumes, collection items, and wearings.
- Search perfumes by brand or name and filter wearing history by time range.
- Keep source characteristics and personal impressions in separate fields.
- Archive and restore collection items while retaining their history.
- View a perfume with its collection items, wearings, and average rating.

Data is stored in PostgreSQL and remains available after application restarts.

## Local setup

You need Python 3.14, [uv](https://docs.astral.sh/uv/), and a running PostgreSQL 18
server with a login role that can own the project databases. The commands below
use PowerShell.

### Install

```powershell
git clone https://github.com/Lueur3/perfume-journal.git
cd perfume-journal
uv sync
```

### Configure the database

Create an empty database named `perfume_journal` in pgAdmin or psql, with your
PostgreSQL role as its owner.

Copy the configuration template into the project root.

```powershell
Copy-Item .env.example .env
```

In `.env`, set `PERFUME_DB_USER` and `PERFUME_DB_PASSWORD` to your PostgreSQL
credentials. Adjust the host, port, and database name if needed. The available
settings are listed in [.env.example](.env.example).

The application loads `.env` automatically. Existing environment variables take
precedence over values in the file. Git ignores `.env`.

Check the connection and apply the checked-in migrations.

```powershell
uv run python -m perfume_journal.db_check
uv run alembic upgrade head
```

The connection check prints the configured database name, normally
`perfume_journal`. Migrations must be applied before using the API.

### Start the API

```powershell
uv run uvicorn perfume_journal.api:app --reload
```

Open the [interactive API documentation](http://127.0.0.1:8000/docs) to send
requests and inspect responses. The [OpenAPI schema](http://127.0.0.1:8000/openapi.json)
describes the endpoints, fields, and validation rules.

## First use

In `/docs`, expand an operation, select **Try it out**, enter its parameters and
JSON body, then select **Execute**.

1. Create a perfume using `POST /perfumes` with the body below. The response is
   `201 Created`. Save the returned `id` as your `perfume_id`.

   ```json
   {
     "brand": "Example House",
     "name": "Journal Demo",
     "concentration": "EDP"
   }
   ```

2. Use that `perfume_id` in `POST /perfumes/{perfume_id}/collection-items` to add
   a sample. Save the response's `id` as your `collection_item_id`.

   ```json
   {
     "kind": "sample",
     "initial_volume_ml": 2.0
   }
   ```

3. Use that `collection_item_id` in
   `POST /collection-items/{collection_item_id}/wearings` to record a wearing.
   Replace the example timestamp with the time you wore it, including its UTC
   offset or `Z`.

   ```json
   {
     "worn_at": "2026-11-26T09:30:00+03:00",
     "rating": 8,
     "comment": "Comfortable for everyday wear"
   }
   ```

4. Call `GET /perfumes/{perfume_id}` with the perfume ID from step 1. The response
   includes the sample and its wearing, and `average_rating` is `8`.

You can use the PATCH operations in `/docs` to edit a collection item, a wearing,
or the perfume's source characteristics and personal impressions. Use
`PUT /perfumes/{perfume_id}` to replace its brand, name, and concentration.

## Working with your data

- Perfume brand and name are required. Concentration is optional. A duplicate
  combination of brand, name, and concentration is rejected with `409 Conflict`,
  ignoring case and surrounding whitespace.
- Archive an item with `PATCH /collection-items/{collection_item_id}` and
  `{"status": "archived"}`. Its history remains readable, and existing wearings
  can be corrected or deleted. Restore it with `{"status": "active"}` before
  adding new wearings.
- A perfume can be deleted only when it has no collection items, including
  archived ones. An item can be deleted only when it has no wearings. Deletions
  are permanent.
- Wearing timestamps require a timezone and are returned in UTC. For example,
  `09:30+03:00` is returned as `06:30Z` on the same date.
- PATCH preserves omitted fields. Explicit `null` clears optional fields such as
  volume, acquisition date, rating, or comment. Item kind, item status, and wearing
  time reject explicit `null`. An empty object `{}` preserves all values.
- Ratings range from 1 to 10. A perfume's average includes rated wearings from
  active and archived items. Unrated wearings are excluded from the calculation,
  and the average is `null` when there are no ratings.

## Development and checks

The API and store tests require a separate PostgreSQL database. Create an empty
database named `perfume_journal_test`, owned by the same role used for local
development. Set `PERFUME_TEST_DB_NAME=perfume_journal_test` in `.env`, keeping
`PERFUME_DB_NAME` pointed at the development database.

Apply migrations to the test database and run the checks.

```powershell
uv run alembic -x environment=test upgrade head
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy --strict .
uv lock --check
```

The test database name must differ from the development database name. Tests
roll back their data changes after each test. PostgreSQL ID sequences can still
advance.

Run `uv run alembic upgrade head` against the development database after pulling
changes that introduce migrations. Migration files are in
[migrations/versions](migrations/versions).
