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
