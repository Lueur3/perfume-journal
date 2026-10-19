from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from perfume_journal.config import get_test_database_url


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def db_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(get_test_database_url())
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def session_factory(
    db_engine: AsyncEngine,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    async with db_engine.connect() as connection:
        transaction = await connection.begin()
        try:
            yield async_sessionmaker(
                bind=connection, join_transaction_mode="create_savepoint"
            )
        finally:
            await transaction.rollback()
