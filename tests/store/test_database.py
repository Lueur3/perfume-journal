import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


@pytest.mark.anyio
async def test_connects_to_test_database(db_engine: AsyncEngine) -> None:
    async with db_engine.connect() as connection:
        query = await connection.execute(text("SELECT current_database()"))
        result: str = query.scalar_one()

        assert result == "perfume_journal_test"
