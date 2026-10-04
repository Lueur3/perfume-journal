from fastapi import FastAPI, HTTPException, status

import perfume_journal.in_memory_store as ims
import perfume_journal.models as mdl

_store = ims.InMemoryStore()

app = FastAPI(title="Perfume Journal")


@app.post("/perfumes", response_model=mdl.Perfume, status_code=status.HTTP_201_CREATED)
def create_perfume(body: mdl.PerfumeCreate) -> mdl.Perfume:
    try:
        return _store.create_perfume(body)
    except ims.DuplicatePerfumeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@app.post(
    "/perfumes/{perfume_id}/collection-items",
    response_model=mdl.CollectionItem,
    status_code=status.HTTP_201_CREATED,
)
def create_collection_item(
    perfume_id: int, body: mdl.CollectionItemCreate
) -> mdl.CollectionItem:
    try:
        return _store.create_collection_item(perfume_id, body)
    except ims.PerfumeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@app.post(
    "/collection-items/{collection_item_id}/wearings",
    response_model=mdl.Wearing,
    status_code=status.HTTP_201_CREATED,
)
def create_wearing(collection_item_id: int, body: mdl.WearingCreate) -> mdl.Wearing:
    try:
        return _store.create_wearing(collection_item_id, body)
    except ims.CollectionItemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@app.get(
    "/perfumes/{perfume_id}",
    response_model=mdl.PerfumeDetails,
    status_code=status.HTTP_200_OK,
)
def get_perfume(perfume_id: int) -> mdl.PerfumeDetails:
    try:
        return _store.get_perfume_details(perfume_id)
    except ims.PerfumeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
