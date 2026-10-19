import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

import perfume_journal.sqlalchemy_store as store
from perfume_journal.errors import DuplicatePerfumeError
from perfume_journal.models import PerfumeCreate
from perfume_journal.orm_models import Perfume as PerfumeRow
from perfume_journal.sqlalchemy_store import create_perfume


@pytest.mark.anyio
async def test_connects_to_test_database(db_engine: AsyncEngine) -> None:
    async with db_engine.connect() as connection:
        query = await connection.execute(text("SELECT current_database()"))
        result: str = query.scalar_one()

        assert result == "perfume_journal_test"


@pytest.mark.anyio
async def test_create_perfume(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    data = PerfumeCreate(brand="Creed", name="Aventus", concentration="EDP")
    mdl_perfume = await create_perfume(session_factory, data)

    assert mdl_perfume.id > 0
    assert mdl_perfume.brand == "Creed"
    assert mdl_perfume.name == "Aventus"
    assert mdl_perfume.concentration == "EDP"

    async with session_factory() as session:
        statement = select(PerfumeRow).where(PerfumeRow.id == mdl_perfume.id)
        result = await session.execute(statement)
        row_perfume = result.scalar_one()

        assert row_perfume.brand == "Creed"
        assert row_perfume.name == "Aventus"
        assert row_perfume.concentration == "EDP"
        assert row_perfume.brand_key == "creed"
        assert row_perfume.name_key == "aventus"
        assert row_perfume.concentration_key == "edp"
        assert row_perfume.brand == mdl_perfume.brand
        assert row_perfume.name == mdl_perfume.name
        assert row_perfume.concentration == mdl_perfume.concentration


@pytest.mark.anyio
@pytest.mark.parametrize(
    "concentration,expected_concentration_key", [(None, None), ("EDP", "edp")]
)
async def test_duplicate_perfume(
    session_factory: async_sessionmaker[AsyncSession],
    concentration: str | None,
    expected_concentration_key: str | None,
) -> None:
    data = PerfumeCreate(brand="Creed", name="Aventus", concentration=concentration)
    mdl_perfume = await create_perfume(session_factory, data)

    duplicate_data = PerfumeCreate(
        brand="CREED", name="aventus", concentration=concentration
    )
    with pytest.raises(DuplicatePerfumeError):
        await create_perfume(session_factory, duplicate_data)

    async with session_factory() as session:
        statement = select(PerfumeRow)
        result = await session.execute(statement)
        row_perfume = result.scalar_one()

        assert row_perfume.id == mdl_perfume.id
        assert row_perfume.brand == mdl_perfume.brand
        assert row_perfume.name == mdl_perfume.name
        assert row_perfume.concentration == concentration
        assert row_perfume.concentration_key == expected_concentration_key
        assert row_perfume.brand == "Creed"
        assert row_perfume.name == "Aventus"
        assert row_perfume.brand_key == "creed"
        assert row_perfume.name_key == "aventus"


@pytest.mark.anyio
async def test_create_perfume_preserves_other_integrity_errors(
    session_factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken_key(_value: str | None) -> None:
        return None

    monkeypatch.setattr(store, "create_key", broken_key)

    data = PerfumeCreate(brand="Creed", name="Aventus", concentration="EDP")

    with pytest.raises(IntegrityError) as caught:
        await store.create_perfume(session_factory, data)

    assert getattr(caught.value.driver_exception, "sqlstate", None) == "23502"

    async with session_factory() as session:
        statement = select(PerfumeRow)
        result = await session.execute(statement)
        row_perfume = result.scalar_one_or_none()

        assert row_perfume is None
