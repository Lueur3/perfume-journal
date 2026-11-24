from fastapi import APIRouter, HTTPException, status

import perfume_journal.models as mdl
import perfume_journal.store.collection_items as sql_store
from perfume_journal.dependencies import SessionFactoryDep
from perfume_journal.errors import (
    CollectionItemHasWearingsError,
    CollectionItemNotFoundError,
    PerfumeNotFoundError,
)

router = APIRouter(tags=["collection_items"])


@router.post(
    "/perfumes/{perfume_id}/collection-items",
    response_model=mdl.CollectionItem,
    status_code=status.HTTP_201_CREATED,
)
async def create_collection_item(
    perfume_id: int,
    body: mdl.CollectionItemCreate,
    session_factory: SessionFactoryDep,
) -> mdl.CollectionItem:
    try:
        return await sql_store.create_collection_item(session_factory, perfume_id, body)
    except PerfumeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.patch(
    "/collection-items/{collection_item_id}",
    response_model=mdl.CollectionItem,
    status_code=status.HTTP_200_OK,
)
async def set_collection_item_status(
    collection_item_id: int,
    session_factory: SessionFactoryDep,
    body: mdl.CollectionItemStatusUpdate,
) -> mdl.CollectionItem:
    try:
        return await sql_store.set_collection_item_status(
            session_factory, collection_item_id, body.status
        )
    except CollectionItemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.delete(
    "/collection-items/{collection_item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_collection_item(
    collection_item_id: int,
    session_factory: SessionFactoryDep,
) -> None:
    try:
        await sql_store.delete_collection_item(session_factory, collection_item_id)
    except CollectionItemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except CollectionItemHasWearingsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.get(
    "/collection-items",
    response_model=list[mdl.CollectionItem],
    status_code=status.HTTP_200_OK,
)
async def list_collection_items(
    session_factory: SessionFactoryDep,
    status: mdl.CollectionItemStatus = "active",
) -> list[mdl.CollectionItem]:
    return await sql_store.list_collection_items(session_factory, status)


@router.get(
    "/collection-items/{collection_item_id}",
    response_model=mdl.CollectionItem,
    status_code=status.HTTP_200_OK,
)
async def get_collection_item(
    session_factory: SessionFactoryDep, collection_item_id: int
) -> mdl.CollectionItem:
    try:
        return await sql_store.get_collection_item(session_factory, collection_item_id)
    except CollectionItemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
