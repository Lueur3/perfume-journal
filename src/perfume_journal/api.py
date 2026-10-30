from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated, cast

from fastapi import Depends, FastAPI, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import perfume_journal.models as mdl
import perfume_journal.sqlalchemy_store as sql_store
from perfume_journal.config import get_database_url
from perfume_journal.errors import (
    CollectionItemNotFoundError,
    DuplicatePerfumeError,
    PerfumeNotFoundError,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    db_url = get_database_url()
    engine = create_async_engine(db_url)
    try:
        app.state.session_factory = async_sessionmaker(engine)
        yield
    finally:
        await engine.dispose()


app = FastAPI(title="Perfume Journal", lifespan=lifespan)


def get_session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    return cast(async_sessionmaker[AsyncSession], request.app.state.session_factory)


@app.post("/perfumes", response_model=mdl.Perfume, status_code=status.HTTP_201_CREATED)
async def create_perfume(
    body: mdl.PerfumeCreate,
    session_factory: Annotated[
        async_sessionmaker[AsyncSession],
        Depends(get_session_factory),
    ],
) -> mdl.Perfume:
    try:
        return await sql_store.create_perfume(session_factory, body)
    except DuplicatePerfumeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@app.post(
    "/perfumes/{perfume_id}/collection-items",
    response_model=mdl.CollectionItem,
    status_code=status.HTTP_201_CREATED,
)
async def create_collection_item(
    perfume_id: int,
    body: mdl.CollectionItemCreate,
    session_factory: Annotated[
        async_sessionmaker[AsyncSession],
        Depends(get_session_factory),
    ],
) -> mdl.CollectionItem:
    try:
        return await sql_store.create_collection_item(session_factory, perfume_id, body)
    except PerfumeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@app.post(
    "/collection-items/{collection_item_id}/wearings",
    response_model=mdl.Wearing,
    status_code=status.HTTP_201_CREATED,
)
async def create_wearing(
    collection_item_id: int,
    body: mdl.WearingCreate,
    session_factory: Annotated[
        async_sessionmaker[AsyncSession],
        Depends(get_session_factory),
    ],
) -> mdl.Wearing:
    try:
        return await sql_store.create_wearing(session_factory, collection_item_id, body)
    except CollectionItemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@app.get(
    "/perfumes/{perfume_id}",
    response_model=mdl.PerfumeDetails,
    status_code=status.HTTP_200_OK,
)
async def get_perfume(
    perfume_id: int,
    session_factory: Annotated[
        async_sessionmaker[AsyncSession],
        Depends(get_session_factory),
    ],
) -> mdl.PerfumeDetails:
    try:
        return await sql_store.get_perfume_details(session_factory, perfume_id)
    except PerfumeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@app.put(
    "/perfumes/{perfume_id}",
    response_model=mdl.Perfume,
    status_code=status.HTTP_200_OK,
)
async def update_perfume(
    perfume_id: int,
    session_factory: Annotated[
        async_sessionmaker[AsyncSession], Depends(get_session_factory)
    ],
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


@app.get("/perfumes", response_model=list[mdl.Perfume], status_code=status.HTTP_200_OK)
async def list_perfumes(
    session_factory: Annotated[
        async_sessionmaker[AsyncSession], Depends(get_session_factory)
    ],
) -> list[mdl.Perfume]:
    return await sql_store.list_perfumes(session_factory)
