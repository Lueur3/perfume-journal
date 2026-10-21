from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

import perfume_journal.sqlalchemy_store as store
from perfume_journal.errors import (
    CollectionItemNotFoundError,
    DuplicatePerfumeError,
    PerfumeNotFoundError,
)
from perfume_journal.models import CollectionItemCreate, PerfumeCreate, WearingCreate
from perfume_journal.orm_models import CollectionItem as CollectionItemRow
from perfume_journal.orm_models import Perfume as PerfumeRow
from perfume_journal.orm_models import Wearing as WearingRow
from perfume_journal.sqlalchemy_store import (
    create_collection_item,
    create_perfume,
    create_wearing,
    get_perfume,
    get_perfume_details,
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


@pytest.mark.anyio
async def test_create_wearing(
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

    data_wearing = WearingCreate(
        worn_at=datetime.fromisoformat("2026-10-02T09:30:00+03:00"),
        rating=7,
        comment="Test comment",
    )
    mdl_wearing = await create_wearing(
        session_factory, collection_item_id=mdl_collection_item.id, data=data_wearing
    )

    assert mdl_wearing.id > 0
    assert mdl_wearing.collection_item_id == mdl_collection_item.id
    expected_zone = timezone(timedelta(hours=3))
    expected_date = datetime(2026, 10, 2, 9, 30, 0, tzinfo=expected_zone)
    assert mdl_wearing.worn_at == expected_date
    assert mdl_wearing.rating == 7
    assert mdl_wearing.comment == "Test comment"

    async with session_factory() as session:
        statement = select(WearingRow).where(
            WearingRow.collection_item_id == mdl_collection_item.id
        )
        query_result = await session.execute(statement)
        result = query_result.scalar_one()

        assert result.id == mdl_wearing.id
        assert result.id > 0
        assert result.collection_item_id == mdl_collection_item.id
        expected_date = datetime.fromisoformat("2026-10-02T09:30:00+03:00")
        assert result.worn_at == expected_date
        assert result.rating == 7
        assert result.comment == "Test comment"
        assert result.worn_at == mdl_wearing.worn_at
        assert result.rating == mdl_wearing.rating
        assert result.comment == mdl_wearing.comment


@pytest.mark.anyio
async def test_no_collection_item_for_wearing(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    data_wearing = WearingCreate(
        worn_at=datetime.fromisoformat("2026-10-02T09:30:00+03:00"),
        rating=7,
        comment="Test comment",
    )

    with pytest.raises(CollectionItemNotFoundError):
        await create_wearing(session_factory, collection_item_id=999, data=data_wearing)

    async with session_factory() as session:
        statement = select(WearingRow)
        query_result = await session.execute(statement)
        result = query_result.scalar_one_or_none()

        assert result is None


@pytest.mark.anyio
async def test_equal_wearing(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    data_perfume = PerfumeCreate(brand="Creed", name="Aventus", concentration="EDP")
    mdl_perfume = await create_perfume(session_factory, data_perfume)

    data_collection_item = CollectionItemCreate(kind="sample")
    mdl_collection_item = await create_collection_item(
        session_factory, perfume_id=mdl_perfume.id, data=data_collection_item
    )

    data_wearing = WearingCreate(
        worn_at=datetime.fromisoformat("2026-10-02T09:30:00+03:00"),
    )
    mdl_wearing_1 = await create_wearing(
        session_factory, collection_item_id=mdl_collection_item.id, data=data_wearing
    )
    mdl_wearing_2 = await create_wearing(
        session_factory, collection_item_id=mdl_collection_item.id, data=data_wearing
    )

    assert mdl_wearing_1.id > 0
    assert mdl_wearing_1.collection_item_id == mdl_collection_item.id
    expected_date = datetime.fromisoformat("2026-10-02T09:30:00+03:00")
    assert mdl_wearing_1.worn_at == expected_date
    assert mdl_wearing_1.rating is None
    assert mdl_wearing_1.comment is None

    assert mdl_wearing_2.id > 0
    assert mdl_wearing_2.collection_item_id == mdl_collection_item.id
    assert mdl_wearing_2.worn_at == expected_date
    assert mdl_wearing_2.rating is None
    assert mdl_wearing_2.comment is None

    async with session_factory() as session:
        statement = select(WearingRow)
        query_result = await session.execute(statement)
        results = query_result.scalars().all()

        assert len(results) == 2
        assert mdl_wearing_1.id != mdl_wearing_2.id
        assert {row.id for row in results} == {
            mdl_wearing_1.id,
            mdl_wearing_2.id,
        }
        for result in results:
            assert result.collection_item_id == mdl_collection_item.id
            assert result.worn_at == expected_date
            assert result.rating is None
            assert result.comment is None


@pytest.mark.anyio
async def test_create_perfume_details(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    data_perfume = PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")
    mdl_perfume = await create_perfume(session_factory, data_perfume)

    data_collection_item_1 = CollectionItemCreate(
        kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
    )
    data_collection_item_2 = CollectionItemCreate(
        kind="bottle", initial_volume_ml=200, acquired_on=date(2026, 9, 20)
    )

    mdl_collection_item_1 = await create_collection_item(
        session_factory, perfume_id=mdl_perfume.id, data=data_collection_item_1
    )
    mdl_collection_item_2 = await create_collection_item(
        session_factory, perfume_id=mdl_perfume.id, data=data_collection_item_2
    )

    data_wearing_1 = WearingCreate(
        worn_at=datetime.fromisoformat("2026-10-02T09:30:00+03:00"),
        rating=10,
        comment="Test comment",
    )
    data_wearing_2 = WearingCreate(
        worn_at=datetime.fromisoformat("2026-10-02T09:30:00+03:00"),
        rating=8,
        comment="Test comment",
    )
    data_wearing_3 = WearingCreate(
        worn_at=datetime.fromisoformat("2026-10-02T09:30:00+03:00"),
        rating=4,
        comment="Test comment",
    )
    data_wearing_4 = WearingCreate(
        worn_at=datetime.fromisoformat("2026-10-02T09:30:00+03:00"),
    )

    mdl_wearing_1 = await create_wearing(
        session_factory,
        collection_item_id=mdl_collection_item_1.id,
        data=data_wearing_1,
    )
    mdl_wearing_2 = await create_wearing(
        session_factory,
        collection_item_id=mdl_collection_item_1.id,
        data=data_wearing_2,
    )
    mdl_wearing_3 = await create_wearing(
        session_factory,
        collection_item_id=mdl_collection_item_2.id,
        data=data_wearing_3,
    )
    mdl_wearing_4 = await create_wearing(
        session_factory,
        collection_item_id=mdl_collection_item_2.id,
        data=data_wearing_4,
    )

    perfume_details = await get_perfume_details(
        session_factory, perfume_id=mdl_perfume.id
    )

    items_by_id = {item.id: item for item in perfume_details.collection_items}
    sample_1 = items_by_id[mdl_collection_item_1.id]
    sample_2 = items_by_id[mdl_collection_item_2.id]

    wearings_by_id_1 = {wearing.id: wearing for wearing in sample_1.wearings}

    assert wearings_by_id_1 == {
        mdl_wearing_1.id: mdl_wearing_1,
        mdl_wearing_2.id: mdl_wearing_2,
    }

    wearings_by_id_2 = {wearing.id: wearing for wearing in sample_2.wearings}

    assert wearings_by_id_2 == {
        mdl_wearing_3.id: mdl_wearing_3,
        mdl_wearing_4.id: mdl_wearing_4,
    }

    assert perfume_details.average_rating == pytest.approx(22 / 3)
    assert len(items_by_id) == 2
    assert len(sample_1.wearings) == 2
    assert len(sample_2.wearings) == 2
    assert perfume_details.id > 0
    assert perfume_details.id == mdl_perfume.id
    assert perfume_details.brand == mdl_perfume.brand
    assert perfume_details.name == mdl_perfume.name
    assert perfume_details.concentration == mdl_perfume.concentration


@pytest.mark.anyio
async def test_perfume_no_collection_items(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    data_perfume = PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")
    mdl_perfume = await create_perfume(session_factory, data_perfume)

    result = await get_perfume_details(session_factory, perfume_id=mdl_perfume.id)

    assert result.id == mdl_perfume.id
    assert result.collection_items == []
    assert result.average_rating is None


@pytest.mark.anyio
async def test_not_exists_perfume(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    with pytest.raises(PerfumeNotFoundError):
        await get_perfume_details(session_factory, perfume_id=999)


@pytest.mark.anyio
async def test_perfume_no_rating(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    data_perfume = PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")
    mdl_perfume = await create_perfume(session_factory, data_perfume)

    data_collection_item_1 = CollectionItemCreate(
        kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
    )
    mdl_collection_item_1 = await create_collection_item(
        session_factory, perfume_id=mdl_perfume.id, data=data_collection_item_1
    )

    data_collection_item_2 = CollectionItemCreate(
        kind="bottle", initial_volume_ml=200, acquired_on=date(2026, 9, 20)
    )
    mdl_collection_item_2 = await create_collection_item(
        session_factory, perfume_id=mdl_perfume.id, data=data_collection_item_2
    )

    data_wearing = WearingCreate(
        worn_at=datetime.fromisoformat("2026-10-02T09:30:00+03:00"),
    )
    mdl_wearing = await create_wearing(
        session_factory, mdl_collection_item_2.id, data_wearing
    )

    perfume_details = await get_perfume_details(session_factory, mdl_perfume.id)

    assert perfume_details.average_rating is None
    assert len(perfume_details.collection_items) == 2

    items_by_id = {item.id: item for item in perfume_details.collection_items}
    sample_1 = items_by_id[mdl_collection_item_1.id]
    sample_2 = items_by_id[mdl_collection_item_2.id]

    assert sample_1.wearings == []
    assert len(sample_2.wearings) == 1
    assert sample_2.wearings[0] == mdl_wearing


@pytest.mark.anyio
async def test_perfume_details_isolation(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    data_perfume_1 = PerfumeCreate(brand="Dior", name="Sauvage", concentration="EDT")
    mdl_perfume_1 = await create_perfume(session_factory, data_perfume_1)

    data_item_1 = CollectionItemCreate(kind="bottle", initial_volume_ml=100)
    mdl_item_1 = await create_collection_item(
        session_factory, perfume_id=mdl_perfume_1.id, data=data_item_1
    )

    data_wearing_1 = WearingCreate(
        worn_at=datetime.fromisoformat("2026-10-01T12:00:00+03:00"),
        rating=2,
    )
    await create_wearing(session_factory, mdl_item_1.id, data_wearing_1)

    data_perfume_2 = PerfumeCreate(
        brand="Chanel", name="Bleu de Chanel", concentration="EDP"
    )
    mdl_perfume_2 = await create_perfume(session_factory, data_perfume_2)

    data_item_2 = CollectionItemCreate(kind="sample", initial_volume_ml=10)
    mdl_item_2 = await create_collection_item(
        session_factory, perfume_id=mdl_perfume_2.id, data=data_item_2
    )

    data_wearing_2 = WearingCreate(
        worn_at=datetime.fromisoformat("2026-10-02T15:00:00+03:00"),
        rating=9,
    )
    mdl_wearing_2 = await create_wearing(session_factory, mdl_item_2.id, data_wearing_2)

    perfume_details = await get_perfume_details(session_factory, mdl_perfume_2.id)

    assert perfume_details.id == mdl_perfume_2.id
    assert perfume_details.average_rating == 9.0
    assert len(perfume_details.collection_items) == 1

    item = perfume_details.collection_items[0]
    assert item.id == mdl_item_2.id
    assert len(item.wearings) == 1
    assert item.wearings[0].id == mdl_wearing_2.id
    assert item.wearings[0].rating == 9
