from datetime import date

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

import perfume_journal.sqlalchemy_store as store
from perfume_journal.errors import DuplicatePerfumeError, PerfumeNotFoundError
from perfume_journal.models import CollectionItemCreate, PerfumeCreate
from perfume_journal.orm_models import CollectionItem as CollectionItemRow
from perfume_journal.orm_models import Perfume as PerfumeRow
from perfume_journal.sqlalchemy_store import (
    create_collection_item,
    create_perfume,
    get_perfume,
)


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


@pytest.mark.anyio
async def test_correct_read_perfume(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    data = PerfumeCreate(brand="Creed", name="Aventus", concentration="EDP")
    await create_perfume(session_factory, data)
    data_2 = PerfumeCreate(brand="Tom Ford", name="Oud Wood", concentration="EDT")
    mdl_perfume_2 = await create_perfume(session_factory, data_2)

    result = await get_perfume(session_factory, mdl_perfume_2.id)

    assert result.id > 0
    assert result.id == mdl_perfume_2.id
    assert result.brand == mdl_perfume_2.brand
    assert result.name == mdl_perfume_2.name
    assert result.concentration == mdl_perfume_2.concentration
    assert result.brand == "Tom Ford"
    assert result.name == "Oud Wood"
    assert result.concentration == "EDT"


@pytest.mark.anyio
async def test_not_found_perfume_error(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    with pytest.raises(PerfumeNotFoundError):
        await get_perfume(session_factory, perfume_id=999)


@pytest.mark.anyio
async def test_create_collection_item(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    data_perfume = PerfumeCreate(brand="Creed", name="Aventus", concentration="EDP")
    mdl_perfume = await create_perfume(session_factory, data_perfume)

    data_collection_item = CollectionItemCreate(
        kind="sample", initial_volume_ml=2.0, acquired_on=date(2026, 10, 19)
    )

    mdl_collection_item = await create_collection_item(
        session_factory, mdl_perfume.id, data_collection_item
    )

    assert mdl_collection_item.id > 0
    assert mdl_collection_item.perfume_id == mdl_perfume.id
    assert mdl_collection_item.kind == "sample"
    assert mdl_collection_item.initial_volume_ml == 2.0
    assert mdl_collection_item.acquired_on == date(2026, 10, 19)
    assert mdl_collection_item.status == "active"

    async with session_factory() as session:
        statement = select(CollectionItemRow).where(
            CollectionItemRow.id == mdl_collection_item.id
        )
        result = await session.execute(statement)
        row_collection_item = result.scalar_one()

        assert row_collection_item.id > 0
        assert row_collection_item.perfume_id == mdl_perfume.id
        assert row_collection_item.kind == "sample"
        assert row_collection_item.initial_volume_ml == 2.0
        assert row_collection_item.acquired_on == date(2026, 10, 19)
        assert row_collection_item.status == "active"


@pytest.mark.anyio
async def test_no_perfume_for_collection_item(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    data_collection_item = CollectionItemCreate(
        kind="sample", initial_volume_ml=2.0, acquired_on=date(2026, 10, 19)
    )

    with pytest.raises(PerfumeNotFoundError):
        await create_collection_item(
            session_factory, perfume_id=999, data=data_collection_item
        )

    async with session_factory() as session:
        statement = select(CollectionItemRow)
        query_result = await session.execute(statement)
        result = query_result.scalar_one_or_none()

        assert result is None


@pytest.mark.anyio
async def test_equal_collection_item(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    data_perfume = PerfumeCreate(brand="Creed", name="Aventus", concentration="EDP")
    mdl_perfume = await create_perfume(session_factory, data_perfume)

    data_collection_item = CollectionItemCreate(kind="sample")
    mdl_collection_item_1 = await create_collection_item(
        session_factory, perfume_id=mdl_perfume.id, data=data_collection_item
    )
    mdl_collection_item_2 = await create_collection_item(
        session_factory, perfume_id=mdl_perfume.id, data=data_collection_item
    )

    assert mdl_collection_item_1.id > 0
    assert mdl_collection_item_1.perfume_id == mdl_perfume.id
    assert mdl_collection_item_1.kind == "sample"
    assert mdl_collection_item_1.initial_volume_ml is None
    assert mdl_collection_item_1.acquired_on is None
    assert mdl_collection_item_1.status == "active"

    assert mdl_collection_item_2.id > 0
    assert mdl_collection_item_2.perfume_id == mdl_perfume.id
    assert mdl_collection_item_2.kind == "sample"
    assert mdl_collection_item_2.initial_volume_ml is None
    assert mdl_collection_item_2.acquired_on is None
    assert mdl_collection_item_2.status == "active"

    async with session_factory() as session:
        statement = select(CollectionItemRow)
        query_result = await session.execute(statement)
        results = query_result.scalars().all()

        assert len(results) == 2
        assert mdl_collection_item_1.id != mdl_collection_item_2.id
        assert {row.id for row in results} == {
            mdl_collection_item_1.id,
            mdl_collection_item_2.id,
        }
