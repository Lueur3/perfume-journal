from fastapi import FastAPI, HTTPException, status

from perfume_journal.in_memory_store import (
    DuplicatePerfumeError,
    InMemoryStore,
    PerfumeNotFoundError,
)
from perfume_journal.models import (
    CollectionItem,
    CollectionItemCreate,
    Perfume,
    PerfumeCreate,
)

_store = InMemoryStore()

app = FastAPI(title="Perfume Journal")


@app.post("/perfumes", response_model=Perfume, status_code=status.HTTP_201_CREATED)
def create_perfume(body: PerfumeCreate) -> Perfume:
    try:
        return _store.create_perfume(body)
    except DuplicatePerfumeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@app.post(
    "/perfumes/{perfume_id}/collection-items",
    response_model=CollectionItem,
    status_code=status.HTTP_201_CREATED,
)
def create_collection_item(
    perfume_id: int, body: CollectionItemCreate
) -> CollectionItem:
    try:
        return _store.create_collection_item(perfume_id, body)
    except PerfumeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
