from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from perfume_journal.config import get_database_url
from perfume_journal.routes.collection_items import router as item_router
from perfume_journal.routes.perfumes import router as perfume_router
from perfume_journal.routes.wearings import router as wearing_router


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
app.include_router(perfume_router)
app.include_router(item_router)
app.include_router(wearing_router)
