from fastapi import APIRouter, HTTPException, status
from pydantic import AwareDatetime

import perfume_journal.models as mdl
import perfume_journal.store.wearings as sql_store
from perfume_journal.dependencies import SessionFactoryDep
from perfume_journal.errors import (
    CollectionItemArchivedError,
    CollectionItemNotFoundError,
    WearingNotFoundError,
)

router = APIRouter(tags=["wearings"])


@router.post(
    "/collection-items/{collection_item_id}/wearings",
    response_model=mdl.Wearing,
    status_code=status.HTTP_201_CREATED,
)
async def create_wearing(
    collection_item_id: int,
    body: mdl.WearingCreate,
    session_factory: SessionFactoryDep,
) -> mdl.Wearing:
    try:
        return await sql_store.create_wearing(session_factory, collection_item_id, body)
    except CollectionItemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except CollectionItemArchivedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.get(
    "/collection-items/{collection_item_id}/wearings",
    response_model=list[mdl.Wearing],
    status_code=status.HTTP_200_OK,
)
async def list_wearings(
    collection_item_id: int,
    session_factory: SessionFactoryDep,
    worn_from: AwareDatetime | None = None,
    worn_before: AwareDatetime | None = None,
) -> list[mdl.Wearing]:
    if worn_from and worn_before and worn_from > worn_before:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="worn_from cannot be after worn_before.",
        )

    try:
        return await sql_store.list_wearings(
            session_factory,
            collection_item_id,
            worn_from=worn_from,
            worn_before=worn_before,
        )
    except CollectionItemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.delete("/wearings/{wearing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wearing(
    wearing_id: int,
    session_factory: SessionFactoryDep,
) -> None:
    try:
        await sql_store.delete_wearing(session_factory, wearing_id)
    except WearingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.get(
    "/wearings/{wearing_id}", response_model=mdl.Wearing, status_code=status.HTTP_200_OK
)
async def get_wearing(
    wearing_id: int, session_factory: SessionFactoryDep
) -> mdl.Wearing:
    try:
        return await sql_store.get_wearing(session_factory, wearing_id)
    except WearingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.patch(
    "/wearings/{wearing_id}", response_model=mdl.Wearing, status_code=status.HTTP_200_OK
)
async def update_wearing(
    wearing_id: int, session_factory: SessionFactoryDep, body: mdl.WearingUpdate
) -> mdl.Wearing:
    try:
        return await sql_store.update_wearing(session_factory, wearing_id, body)
    except WearingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
