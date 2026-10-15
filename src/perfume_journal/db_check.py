import asyncio
import os

from sqlalchemy import URL, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


async def main() -> None:
    db_name = os.environ["PERFUME_DB_NAME"]
    db_port = int(os.environ["PERFUME_DB_PORT"])
    db_host = os.environ["PERFUME_DB_HOST"]
    db_user = os.environ["PERFUME_DB_USER"]
    db_password = os.environ["PERFUME_DB_PASSWORD"]

    db_url = URL.create(
        drivername="postgresql+asyncpg",
        username=db_user,
        host=db_host,
        port=db_port,
        database=db_name,
        password=db_password,
    )

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
