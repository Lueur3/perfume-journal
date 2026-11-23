from fastapi import APIRouter, HTTPException, status

import perfume_journal.models as mdl
import perfume_journal.store.perfumes as sql_store
from perfume_journal.dependencies import SessionFactoryDep
from perfume_journal.errors import (
    DuplicatePerfumeError,
    PerfumeHasCollectionItemsError,
    PerfumeNotFoundError,
)

router = APIRouter(tags=["perfumes"])


@router.post(
    "/perfumes", response_model=mdl.Perfume, status_code=status.HTTP_201_CREATED
)
async def create_perfume(
    body: mdl.PerfumeCreate,
    session_factory: SessionFactoryDep,
) -> mdl.Perfume:
    try:
        return await sql_store.create_perfume(session_factory, body)
    except DuplicatePerfumeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.get(
    "/perfumes/{perfume_id}",
    response_model=mdl.PerfumeDetails,
    status_code=status.HTTP_200_OK,
)
async def get_perfume(
    perfume_id: int,
    session_factory: SessionFactoryDep,
) -> mdl.PerfumeDetails:
    try:
        return await sql_store.get_perfume_details(session_factory, perfume_id)
    except PerfumeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.put(
    "/perfumes/{perfume_id}",
    response_model=mdl.Perfume,
    status_code=status.HTTP_200_OK,
)
async def update_perfume(
    perfume_id: int,
    session_factory: SessionFactoryDep,
    body: mdl.PerfumeCreate,
) -> mdl.Perfume:
    try:
        return await sql_store.update_perfume(session_factory, perfume_id, body)
    except PerfumeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except DuplicatePerfumeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.get(
    "/perfumes", response_model=list[mdl.Perfume], status_code=status.HTTP_200_OK
)
async def list_perfumes(
    session_factory: SessionFactoryDep,
    q: str | None = None,
) -> list[mdl.Perfume]:
    return await sql_store.list_perfumes(session_factory, q=q)


@router.delete("/perfumes/{perfume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_perfume(
    perfume_id: int,
    session_factory: SessionFactoryDep,
) -> None:
    try:
        await sql_store.delete_perfume(session_factory, perfume_id)
    except PerfumeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except PerfumeHasCollectionItemsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.patch(
    "/perfumes/{perfume_id}/source",
    response_model=mdl.PerfumeSource,
    status_code=status.HTTP_200_OK,
)
async def update_perfume_source(
    perfume_id: int,
    session_factory: SessionFactoryDep,
    body: mdl.PerfumeSourceUpdate,
) -> mdl.PerfumeSource:
    try:
        return await sql_store.update_perfume_source(
            session_factory, perfume_id, data=body
        )
    except PerfumeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.patch(
    "/perfumes/{perfume_id}/personal",
    response_model=mdl.PerfumePersonal,
    status_code=status.HTTP_200_OK,
)
async def update_perfume_personal(
    perfume_id: int,
    session_factory: SessionFactoryDep,
    body: mdl.PerfumePersonalUpdate,
) -> mdl.PerfumePersonal:
    try:
        return await sql_store.update_perfume_personal(
            session_factory, perfume_id, data=body
        )
    except PerfumeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
