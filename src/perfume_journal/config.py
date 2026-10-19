import os

from dotenv import load_dotenv
from sqlalchemy import URL


def get_database_url() -> URL:
    load_dotenv()
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

    return db_url


def get_test_database_url() -> URL:
    db_url = get_database_url()
    db_test_name = os.environ["PERFUME_TEST_DB_NAME"]
    if db_test_name == db_url.database or not db_test_name:
        raise ValueError(
            f"Invalid test database name: '{db_test_name}'. "
            f"It cannot be empty or match the main database name ('{db_url.database}')."
        )

    db_test_url = db_url.set(database=db_test_name)

    return db_test_url
