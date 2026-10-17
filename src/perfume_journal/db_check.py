import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from perfume_journal.config import get_database_url


async def main() -> None:
    db_url = get_database_url()
    engine = create_async_engine(db_url)

    session_factory = async_sessionmaker(engine)

    try:
        async with session_factory() as session:
            query = text("SELECT current_database()")
            result = await session.execute(query)
            curr_db: str = result.scalar_one()

            print(curr_db)

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
