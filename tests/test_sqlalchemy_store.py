from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

import perfume_journal.sqlalchemy_store as store
from perfume_journal.errors import (
    CollectionItemArchivedError,
    CollectionItemHasWearingsError,
    CollectionItemNotFoundError,
    DuplicatePerfumeError,
    PerfumeHasCollectionItemsError,
    PerfumeNotFoundError,
    WearingNotFoundError,
)
from perfume_journal.models import CollectionItemCreate, PerfumeCreate, WearingCreate
from perfume_journal.orm_models import CollectionItem as CollectionItemRow
from perfume_journal.orm_models import Perfume as PerfumeRow
from perfume_journal.orm_models import Wearing as WearingRow
from perfume_journal.sqlalchemy_store import (
    create_collection_item,
    create_perfume,
    create_wearing,
    delete_collection_item,
    delete_perfume,
    delete_wearing,
    get_perfume,
    get_perfume_details,
    list_collection_items,
    list_perfumes,
    list_wearings,
    set_collection_item_status,
    update_perfume,
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
    perfume = await create_perfume(session_factory, data)

    assert perfume.id > 0
    assert perfume.brand == "Creed"
    assert perfume.name == "Aventus"
    assert perfume.concentration == "EDP"

    async with session_factory() as session:
        statement = select(PerfumeRow).where(PerfumeRow.id == perfume.id)
        result = await session.execute(statement)
        perfume_row = result.scalar_one()

        assert perfume_row.brand == "Creed"
        assert perfume_row.name == "Aventus"
        assert perfume_row.concentration == "EDP"
        assert perfume_row.brand_key == "creed"
        assert perfume_row.name_key == "aventus"
        assert perfume_row.concentration_key == "edp"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "concentration,expected_concentration_key", [(None, None), ("EDP", "edp")]
)
async def test_duplicate_perfume(
    session_factory: async_sessionmaker[AsyncSession],
    concentration: str | None,
    expected_concentration_key: str | None,
) -> None:
    data = PerfumeCreate(brand="Tom Ford", name="Oud Wood", concentration=concentration)
    perfume = await create_perfume(session_factory, data)

    duplicate_data = PerfumeCreate(
        brand="tom   ford", name="OUD  WOOD", concentration=concentration
    )
    with pytest.raises(DuplicatePerfumeError):
        await create_perfume(session_factory, duplicate_data)

    async with session_factory() as session:
        statement = select(PerfumeRow)
        result = await session.execute(statement)
        perfume_row = result.scalar_one()

        assert perfume_row.id == perfume.id
        assert perfume_row.brand == "Tom Ford"
        assert perfume_row.name == "Oud Wood"
        assert perfume_row.concentration == concentration
        assert perfume_row.concentration_key == expected_concentration_key
        assert perfume_row.brand_key == "tom ford"
        assert perfume_row.name_key == "oud wood"


@pytest.mark.anyio
async def test_create_perfume_different_concentrations(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    first_data = PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")
    first_perfume = await create_perfume(session_factory, first_data)

    second_data = PerfumeCreate(brand="Creed", name="Aventus", concentration="EDP")
    second_perfume = await create_perfume(session_factory, second_data)

    assert first_perfume.id != second_perfume.id

    async with session_factory() as session:
        statement = select(PerfumeRow)
        result_query = await session.execute(statement)
        results = result_query.scalars().all()

    assert len(results) == 2
    assert {row.id for row in results} == {first_perfume.id, second_perfume.id}
    assert {row.concentration for row in results} == {"EDT", "EDP"}


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
        perfume_row = result.scalar_one_or_none()

        assert perfume_row is None


@pytest.mark.anyio
async def test_get_perfume_by_id(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    first_data = PerfumeCreate(brand="Creed", name="Aventus", concentration="EDP")
    await create_perfume(session_factory, first_data)
    target_data = PerfumeCreate(brand="Tom Ford", name="Oud Wood", concentration="EDT")
    target_perfume = await create_perfume(session_factory, target_data)

    result = await get_perfume(session_factory, target_perfume.id)

    assert result == target_perfume


@pytest.mark.anyio
async def test_get_perfume_not_found(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    with pytest.raises(PerfumeNotFoundError):
        await get_perfume(session_factory, perfume_id=999)


@pytest.mark.anyio
async def test_create_collection_item(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await create_perfume(
        session_factory,
        PerfumeCreate(brand="Creed", name="Aventus", concentration="EDP"),
    )
    item_data = CollectionItemCreate(
        kind="sample", initial_volume_ml=2.0, acquired_on=date(2026, 10, 19)
    )
    item = await create_collection_item(session_factory, perfume.id, item_data)

    assert item.id > 0
    assert item.perfume_id == perfume.id
    assert item.kind == "sample"
    assert item.initial_volume_ml == 2.0
    assert item.acquired_on == date(2026, 10, 19)
    assert item.status == "active"

    async with session_factory() as session:
        statement = select(CollectionItemRow).where(CollectionItemRow.id == item.id)
        result = await session.execute(statement)
        item_row = result.scalar_one()

        assert item_row.id == item.id
        assert item_row.perfume_id == perfume.id
        assert item_row.kind == "sample"
        assert item_row.initial_volume_ml == 2.0
        assert item_row.acquired_on == date(2026, 10, 19)
        assert item_row.status == "active"


@pytest.mark.anyio
async def test_create_collection_item_missing_perfume_raises_not_found(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    item_data = CollectionItemCreate(
        kind="sample", initial_volume_ml=2.0, acquired_on=date(2026, 10, 19)
    )

    with pytest.raises(PerfumeNotFoundError):
        await create_collection_item(session_factory, perfume_id=999, data=item_data)

    async with session_factory() as session:
        statement = select(CollectionItemRow)
        result = await session.execute(statement)
        assert result.scalar_one_or_none() is None


@pytest.mark.anyio
async def test_create_multiple_identical_collection_items(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await create_perfume(
        session_factory,
        PerfumeCreate(brand="Creed", name="Aventus", concentration="EDP"),
    )
    item_data = CollectionItemCreate(kind="sample")
    first_item = await create_collection_item(
        session_factory, perfume_id=perfume.id, data=item_data
    )
    second_item = await create_collection_item(
        session_factory, perfume_id=perfume.id, data=item_data
    )

    assert first_item.id > 0
    assert first_item.perfume_id == perfume.id
    assert first_item.kind == "sample"
    assert first_item.initial_volume_ml is None
    assert first_item.acquired_on is None
    assert first_item.status == "active"

    assert second_item.id > 0
    assert second_item.perfume_id == perfume.id
    assert second_item.kind == "sample"
    assert second_item.initial_volume_ml is None
    assert second_item.acquired_on is None
    assert second_item.status == "active"

    assert first_item.id != second_item.id

    async with session_factory() as session:
        statement = select(CollectionItemRow)
        result = await session.execute(statement)
        results = result.scalars().all()

    assert len(results) == 2
    assert {row.id for row in results} == {first_item.id, second_item.id}


@pytest.mark.anyio
async def test_create_wearing(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await create_perfume(
        session_factory,
        PerfumeCreate(brand="Creed", name="Aventus", concentration="EDP"),
    )
    item_data = CollectionItemCreate(
        kind="sample", initial_volume_ml=2.0, acquired_on=date(2026, 10, 19)
    )
    item = await create_collection_item(session_factory, perfume.id, item_data)

    expected_worn_at = datetime(
        2026, 10, 2, 9, 30, 0, tzinfo=timezone(timedelta(hours=3))
    )
    wearing_data = WearingCreate(
        worn_at=expected_worn_at,
        rating=7,
        comment="Test comment",
    )
    wearing = await create_wearing(
        session_factory, collection_item_id=item.id, data=wearing_data
    )

    assert wearing.id > 0
    assert wearing.collection_item_id == item.id
    assert wearing.worn_at == expected_worn_at
    assert wearing.rating == 7
    assert wearing.comment == "Test comment"

    async with session_factory() as session:
        statement = select(WearingRow).where(WearingRow.collection_item_id == item.id)
        result = await session.execute(statement)
        wearing_row = result.scalar_one()

        assert wearing_row.id == wearing.id
        assert wearing_row.collection_item_id == item.id
        assert wearing_row.worn_at == expected_worn_at
        assert wearing_row.rating == 7
        assert wearing_row.comment == "Test comment"


@pytest.mark.anyio
async def test_create_wearing_missing_item_raises_not_found(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    wearing_data = WearingCreate(
        worn_at=datetime.fromisoformat("2026-10-02T09:30:00+03:00"),
        rating=7,
        comment="Test comment",
    )

    with pytest.raises(CollectionItemNotFoundError):
        await create_wearing(session_factory, collection_item_id=999, data=wearing_data)

    async with session_factory() as session:
        statement = select(WearingRow)
        result = await session.execute(statement)
        assert result.scalar_one_or_none() is None


@pytest.mark.anyio
async def test_create_multiple_identical_wearings(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await create_perfume(
        session_factory,
        PerfumeCreate(brand="Creed", name="Aventus", concentration="EDP"),
    )
    item_data = CollectionItemCreate(kind="sample")
    item = await create_collection_item(
        session_factory, perfume_id=perfume.id, data=item_data
    )

    expected_worn_at = datetime.fromisoformat("2026-10-02T09:30:00+03:00")
    wearing_data = WearingCreate(worn_at=expected_worn_at)
    first_wearing = await create_wearing(
        session_factory, collection_item_id=item.id, data=wearing_data
    )
    second_wearing = await create_wearing(
        session_factory, collection_item_id=item.id, data=wearing_data
    )

    assert first_wearing.id > 0
    assert first_wearing.collection_item_id == item.id
    assert first_wearing.worn_at == expected_worn_at
    assert first_wearing.rating is None
    assert first_wearing.comment is None

    assert second_wearing.id > 0
    assert second_wearing.collection_item_id == item.id
    assert second_wearing.worn_at == expected_worn_at
    assert second_wearing.rating is None
    assert second_wearing.comment is None

    assert first_wearing.id != second_wearing.id

    async with session_factory() as session:
        statement = select(WearingRow)
        result = await session.execute(statement)
        results = result.scalars().all()

    assert len(results) == 2
    assert {row.id for row in results} == {first_wearing.id, second_wearing.id}
    for row in results:
        assert row.collection_item_id == item.id
        assert row.worn_at == expected_worn_at
        assert row.rating is None
        assert row.comment is None


@pytest.mark.anyio
async def test_get_perfume_details_includes_wearings_and_average_rating(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await create_perfume(
        session_factory,
        PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )
    first_item = await create_collection_item(
        session_factory,
        perfume_id=perfume.id,
        data=CollectionItemCreate(
            kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
        ),
    )
    second_item = await create_collection_item(
        session_factory,
        perfume_id=perfume.id,
        data=CollectionItemCreate(
            kind="bottle", initial_volume_ml=200, acquired_on=date(2026, 9, 20)
        ),
    )

    first_wearing = await create_wearing(
        session_factory,
        collection_item_id=first_item.id,
        data=WearingCreate(
            worn_at=datetime.fromisoformat("2026-10-02T09:30:00+03:00"),
            rating=10,
            comment="Test comment",
        ),
    )
    second_wearing = await create_wearing(
        session_factory,
        collection_item_id=first_item.id,
        data=WearingCreate(
            worn_at=datetime.fromisoformat("2026-10-02T09:30:00+03:00"),
            rating=8,
            comment="Test comment",
        ),
    )
    third_wearing = await create_wearing(
        session_factory,
        collection_item_id=second_item.id,
        data=WearingCreate(
            worn_at=datetime.fromisoformat("2026-10-02T09:30:00+03:00"),
            rating=4,
            comment="Test comment",
        ),
    )
    fourth_wearing = await create_wearing(
        session_factory,
        collection_item_id=second_item.id,
        data=WearingCreate(
            worn_at=datetime.fromisoformat("2026-10-02T09:30:00+03:00"),
        ),
    )

    details = await get_perfume_details(session_factory, perfume_id=perfume.id)

    items_by_id = {item.id: item for item in details.collection_items}
    assert len(items_by_id) == 2

    first_item_details = items_by_id[first_item.id]
    second_item_details = items_by_id[second_item.id]

    assert len(first_item_details.wearings) == 2
    wearings_by_id_1 = {wearing.id: wearing for wearing in first_item_details.wearings}
    assert wearings_by_id_1 == {
        first_wearing.id: first_wearing,
        second_wearing.id: second_wearing,
    }

    assert len(second_item_details.wearings) == 2
    wearings_by_id_2 = {wearing.id: wearing for wearing in second_item_details.wearings}
    assert wearings_by_id_2 == {
        third_wearing.id: third_wearing,
        fourth_wearing.id: fourth_wearing,
    }

    assert details.average_rating == pytest.approx(22 / 3)
    assert details.id == perfume.id
    assert details.brand == perfume.brand
    assert details.name == perfume.name
    assert details.concentration == perfume.concentration


@pytest.mark.anyio
async def test_get_perfume_details_without_collection_items(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await create_perfume(
        session_factory,
        PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )

    details = await get_perfume_details(session_factory, perfume_id=perfume.id)

    assert details.id == perfume.id
    assert details.collection_items == []
    assert details.average_rating is None


@pytest.mark.anyio
async def test_get_perfume_details_not_found(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    with pytest.raises(PerfumeNotFoundError):
        await get_perfume_details(session_factory, perfume_id=999)


@pytest.mark.anyio
async def test_get_perfume_details_without_ratings(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await create_perfume(
        session_factory,
        PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )
    first_item = await create_collection_item(
        session_factory,
        perfume_id=perfume.id,
        data=CollectionItemCreate(
            kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
        ),
    )
    second_item = await create_collection_item(
        session_factory,
        perfume_id=perfume.id,
        data=CollectionItemCreate(
            kind="bottle", initial_volume_ml=200, acquired_on=date(2026, 9, 20)
        ),
    )
    wearing = await create_wearing(
        session_factory,
        second_item.id,
        WearingCreate(
            worn_at=datetime.fromisoformat("2026-10-02T09:30:00+03:00"),
        ),
    )

    details = await get_perfume_details(session_factory, perfume.id)

    assert details.average_rating is None
    assert len(details.collection_items) == 2

    items_by_id = {item.id: item for item in details.collection_items}
    assert items_by_id[first_item.id].wearings == []
    assert items_by_id[second_item.id].wearings == [wearing]


@pytest.mark.anyio
async def test_perfume_details_isolation(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    first_perfume = await create_perfume(
        session_factory,
        PerfumeCreate(brand="Dior", name="Sauvage", concentration="EDT"),
    )
    first_item = await create_collection_item(
        session_factory,
        perfume_id=first_perfume.id,
        data=CollectionItemCreate(kind="bottle", initial_volume_ml=100),
    )
    await create_wearing(
        session_factory,
        first_item.id,
        WearingCreate(
            worn_at=datetime.fromisoformat("2026-10-01T12:00:00+03:00"),
            rating=2,
        ),
    )

    second_perfume = await create_perfume(
        session_factory,
        PerfumeCreate(brand="Chanel", name="Bleu de Chanel", concentration="EDP"),
    )
    second_item = await create_collection_item(
        session_factory,
        perfume_id=second_perfume.id,
        data=CollectionItemCreate(kind="sample", initial_volume_ml=10),
    )
    second_wearing = await create_wearing(
        session_factory,
        second_item.id,
        WearingCreate(
            worn_at=datetime.fromisoformat("2026-10-02T15:00:00+03:00"),
            rating=9,
        ),
    )

    details = await get_perfume_details(session_factory, second_perfume.id)

    assert details.id == second_perfume.id
    assert details.average_rating == 9.0
    assert len(details.collection_items) == 1

    item = details.collection_items[0]
    assert item.id == second_item.id
    assert len(item.wearings) == 1
    assert item.wearings[0].id == second_wearing.id
    assert item.wearings[0].rating == 9


@pytest.mark.anyio
async def test_update_perfume(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    original_perfume = await create_perfume(
        session_factory,
        PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )

    update_data = PerfumeCreate(brand="Tom Ford", name="Oud Wood")
    updated_perfume = await update_perfume(
        session_factory, original_perfume.id, update_data
    )

    assert updated_perfume.id == original_perfume.id
    assert updated_perfume.brand == "Tom Ford"
    assert updated_perfume.name == "Oud Wood"
    assert updated_perfume.concentration is None

    async with session_factory() as session:
        statement = select(PerfumeRow).where(PerfumeRow.id == original_perfume.id)
        result = await session.execute(statement)
        perfume_row = result.scalar_one()

        assert perfume_row.brand == "Tom Ford"
        assert perfume_row.name == "Oud Wood"
        assert perfume_row.concentration is None
        assert perfume_row.brand_key == "tom ford"
        assert perfume_row.name_key == "oud wood"
        assert perfume_row.concentration_key is None


@pytest.mark.anyio
async def test_update_perfume_duplicate_raises_conflict(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    existing_perfume = await create_perfume(
        session_factory, PerfumeCreate(brand="Tom Ford", name="Oud Wood")
    )
    target_perfume = await create_perfume(
        session_factory, PerfumeCreate(brand="Creed", name="Aventus")
    )

    duplicate_data = PerfumeCreate(brand="tom  ford", name="oud   wood")

    with pytest.raises(DuplicatePerfumeError):
        await update_perfume(session_factory, target_perfume.id, duplicate_data)

    async with session_factory() as session:
        statement = select(PerfumeRow)
        result = await session.execute(statement)
        results = result.scalars().all()

        assert {row.id for row in results} == {
            existing_perfume.id,
            target_perfume.id,
        }
        by_id = {row.id: row for row in results}

        existing_row = by_id[existing_perfume.id]
        assert existing_row.brand == "Tom Ford"
        assert existing_row.name == "Oud Wood"
        assert existing_row.concentration is None
        assert existing_row.brand_key == "tom ford"
        assert existing_row.name_key == "oud wood"
        assert existing_row.concentration_key is None

        target_row = by_id[target_perfume.id]
        assert target_row.brand == "Creed"
        assert target_row.name == "Aventus"
        assert target_row.concentration is None
        assert target_row.brand_key == "creed"
        assert target_row.name_key == "aventus"
        assert target_row.concentration_key is None


@pytest.mark.anyio
async def test_update_missing_perfume_raises_not_found(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    data = PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")

    with pytest.raises(PerfumeNotFoundError):
        await update_perfume(session_factory, perfume_id=999, data=data)

    async with session_factory() as session:
        statement = select(PerfumeRow)
        result = await session.execute(statement)
        assert result.scalar_one_or_none() is None


@pytest.mark.anyio
async def test_list_perfumes_empty(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    assert await list_perfumes(session_factory) == []


@pytest.mark.anyio
async def test_list_perfumes(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    first_perfume = await create_perfume(
        session_factory,
        PerfumeCreate(brand="Tom Ford", name="Oud Wood", concentration="EDT"),
    )
    second_perfume = await create_perfume(
        session_factory, PerfumeCreate(brand="Creed", name="Aventus")
    )

    perfumes = await list_perfumes(session_factory)

    assert perfumes == [first_perfume, second_perfume]


@pytest.mark.anyio
async def test_list_perfumes_search(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    first_perfume = await create_perfume(
        session_factory,
        PerfumeCreate(brand="Tom Ford", name="Oud Wood", concentration="EDT"),
    )
    second_perfume = await create_perfume(
        session_factory, PerfumeCreate(brand="Creed", name="Aventus")
    )
    await create_perfume(
        session_factory, PerfumeCreate(brand="Chanel", name="Bleu de Chanel")
    )

    find_perfume_1 = await list_perfumes(session_factory, q="ford")
    find_perfume_2 = await list_perfumes(session_factory, q="AVEN  ")

    assert find_perfume_1 == [first_perfume]
    assert find_perfume_2 == [second_perfume]


@pytest.mark.anyio
async def test_list_perfumes_search_no_matches(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await create_perfume(
        session_factory,
        PerfumeCreate(brand="Tom Ford", name="Oud Wood", concentration="EDT"),
    )

    assert await list_perfumes(session_factory, q="Dior") == []


@pytest.mark.anyio
async def test_archive_and_restore_collection_item(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await create_perfume(
        session_factory,
        PerfumeCreate(brand="Tom Ford", name="Oud Wood", concentration="EDT"),
    )
    item = await create_collection_item(
        session_factory,
        perfume_id=perfume.id,
        data=CollectionItemCreate(
            kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
        ),
    )
    wearing = await create_wearing(
        session_factory,
        collection_item_id=item.id,
        data=WearingCreate(
            worn_at=datetime.fromisoformat("2026-10-02T09:30:00+03:00"),
            rating=10,
            comment="Test comment",
        ),
    )

    archived_item = await set_collection_item_status(
        session_factory, item.id, "archived"
    )
    assert archived_item.status == "archived"
    assert archived_item.id == item.id
    assert archived_item.perfume_id == perfume.id

    details_archived = await get_perfume_details(session_factory, perfume_id=perfume.id)
    assert len(details_archived.collection_items) == 1
    item_archived = details_archived.collection_items[0]
    assert item_archived.id == item.id
    assert item_archived.status == "archived"
    assert item_archived.wearings == [wearing]

    archived_item_repeat = await set_collection_item_status(
        session_factory, item.id, "archived"
    )
    assert archived_item_repeat == archived_item

    active_item = await set_collection_item_status(session_factory, item.id, "active")
    assert active_item == item

    details_active = await get_perfume_details(session_factory, perfume_id=perfume.id)
    assert len(details_active.collection_items) == 1
    item_active = details_active.collection_items[0]
    assert item_active.id == item.id
    assert item_active.status == "active"
    assert item_active.wearings == [wearing]


@pytest.mark.anyio
async def test_set_collection_item_status_not_found(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    with pytest.raises(CollectionItemNotFoundError):
        await set_collection_item_status(
            session_factory, collection_item_id=999, status="archived"
        )


@pytest.mark.anyio
async def test_create_wearing_for_archived_item_raises_conflict(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await create_perfume(
        session_factory,
        PerfumeCreate(brand="Tom Ford", name="Oud Wood", concentration="EDT"),
    )
    item = await create_collection_item(
        session_factory,
        perfume_id=perfume.id,
        data=CollectionItemCreate(
            kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
        ),
    )
    await set_collection_item_status(session_factory, item.id, "archived")

    wearing_data = WearingCreate(
        worn_at=datetime.fromisoformat("2026-10-02T09:30:00+03:00"),
        rating=10,
        comment="Test comment",
    )

    with pytest.raises(CollectionItemArchivedError):
        await create_wearing(
            session_factory,
            collection_item_id=item.id,
            data=wearing_data,
        )

    details_archived = await get_perfume_details(session_factory, perfume_id=perfume.id)
    assert len(details_archived.collection_items) == 1
    item_archived = details_archived.collection_items[0]
    assert item_archived.id == item.id
    assert item_archived.status == "archived"
    assert item_archived.wearings == []

    await set_collection_item_status(session_factory, item.id, "active")

    wearing = await create_wearing(
        session_factory,
        collection_item_id=item.id,
        data=wearing_data,
    )

    details_active = await get_perfume_details(session_factory, perfume_id=perfume.id)
    assert len(details_active.collection_items) == 1
    item_active = details_active.collection_items[0]
    assert item_active.id == item.id
    assert item_active.status == "active"
    assert item_active.wearings == [wearing]


@pytest.mark.anyio
async def test_list_collection_items_empty(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    assert await list_collection_items(session_factory, "active") == []


@pytest.mark.anyio
async def test_list_collection_items_filters_by_status(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await create_perfume(
        session_factory,
        PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )
    first_item = await create_collection_item(
        session_factory,
        perfume_id=perfume.id,
        data=CollectionItemCreate(
            kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
        ),
    )
    second_item = await create_collection_item(
        session_factory,
        perfume_id=perfume.id,
        data=CollectionItemCreate(
            kind="bottle", initial_volume_ml=200, acquired_on=date(2026, 9, 20)
        ),
    )

    archived_item = await set_collection_item_status(
        session_factory, second_item.id, "archived"
    )

    assert await list_collection_items(session_factory, "active") == [first_item]
    assert await list_collection_items(session_factory, "archived") == [archived_item]


@pytest.mark.anyio
async def test_list_wearings_returns_item_history_newest_first(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await create_perfume(
        session_factory,
        PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )
    item = await create_collection_item(
        session_factory,
        perfume_id=perfume.id,
        data=CollectionItemCreate(
            kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
        ),
    )
    other_item = await create_collection_item(
        session_factory,
        perfume_id=perfume.id,
        data=CollectionItemCreate(
            kind="bottle", initial_volume_ml=150, acquired_on=date(2026, 9, 15)
        ),
    )

    older_wearing = await create_wearing(
        session_factory,
        item.id,
        WearingCreate(
            worn_at=datetime.fromisoformat("2026-10-28T15:00:00+03:00"),
            rating=9,
        ),
    )
    newer_wearing = await create_wearing(
        session_factory,
        item.id,
        WearingCreate(
            worn_at=datetime.fromisoformat("2026-11-05T15:00:00+03:00"),
            rating=9,
        ),
    )
    await create_wearing(
        session_factory,
        other_item.id,
        WearingCreate(
            worn_at=datetime.fromisoformat("2026-10-15T15:00:00+03:00"),
            rating=9,
        ),
    )

    wearings = await list_wearings(session_factory, item.id)

    assert wearings == [newer_wearing, older_wearing]


@pytest.mark.anyio
async def test_list_wearings_empty(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await create_perfume(
        session_factory,
        PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )
    item = await create_collection_item(
        session_factory,
        perfume_id=perfume.id,
        data=CollectionItemCreate(
            kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
        ),
    )

    assert await list_wearings(session_factory, item.id) == []


@pytest.mark.anyio
async def test_list_wearings_not_found(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    with pytest.raises(CollectionItemNotFoundError):
        await list_wearings(session_factory, collection_item_id=999)


@pytest.mark.anyio
async def test_list_wearings_filter_by_date_range(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await create_perfume(
        session_factory,
        PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )
    item = await create_collection_item(
        session_factory,
        perfume_id=perfume.id,
        data=CollectionItemCreate(
            kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
        ),
    )

    wearing_lower = await create_wearing(
        session_factory,
        item.id,
        WearingCreate(
            worn_at=datetime.fromisoformat("2026-10-28T10:00:00+03:00"),
            rating=9,
        ),
    )
    wearing_middle = await create_wearing(
        session_factory,
        item.id,
        WearingCreate(
            worn_at=datetime.fromisoformat("2026-11-01T12:00:00+03:00"),
            rating=9,
        ),
    )
    await create_wearing(
        session_factory,
        item.id,
        WearingCreate(
            worn_at=datetime.fromisoformat("2026-11-05T10:00:00+03:00"),
            rating=9,
        ),
    )

    t_zone = timezone(timedelta(hours=3))
    worn_from = datetime(2026, 10, 28, 10, 0, tzinfo=t_zone)
    worn_before = datetime(2026, 11, 5, 10, 0, tzinfo=t_zone)

    wearings = await list_wearings(
        session_factory,
        item.id,
        worn_from=worn_from,
        worn_before=worn_before,
    )

    assert wearings == [wearing_middle, wearing_lower]


@pytest.mark.anyio
async def test_delete_active_collection_item(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await create_perfume(
        session_factory,
        PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )
    item = await create_collection_item(
        session_factory,
        perfume_id=perfume.id,
        data=CollectionItemCreate(
            kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
        ),
    )

    await delete_collection_item(session_factory, item.id)

    async with session_factory() as session:
        res = await session.scalars(select(CollectionItemRow))
        assert res.all() == []

        perfume_row = await session.get(PerfumeRow, perfume.id)
        assert perfume_row is not None


@pytest.mark.anyio
async def test_delete_archived_collection_item(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await create_perfume(
        session_factory,
        PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )
    item = await create_collection_item(
        session_factory,
        perfume_id=perfume.id,
        data=CollectionItemCreate(
            kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
        ),
    )
    archived_item = await set_collection_item_status(
        session_factory, item.id, "archived"
    )

    await delete_collection_item(session_factory, archived_item.id)

    async with session_factory() as session:
        res = await session.scalars(select(CollectionItemRow))
        assert res.all() == []

        perfume_row = await session.get(PerfumeRow, perfume.id)
        assert perfume_row is not None


@pytest.mark.anyio
async def test_delete_collection_item_not_found(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    with pytest.raises(CollectionItemNotFoundError):
        await delete_collection_item(session_factory, collection_item_id=999)


@pytest.mark.anyio
async def test_delete_collection_item_with_wearings_raises_conflict(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await create_perfume(
        session_factory,
        PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )
    item = await create_collection_item(
        session_factory,
        perfume_id=perfume.id,
        data=CollectionItemCreate(
            kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
        ),
    )
    wearing = await create_wearing(
        session_factory,
        item.id,
        WearingCreate(
            worn_at=datetime.fromisoformat("2026-10-02T15:00:00+03:00"),
            rating=9,
        ),
    )

    with pytest.raises(CollectionItemHasWearingsError):
        await delete_collection_item(session_factory, item.id)

    details = await get_perfume_details(session_factory, perfume.id)

    assert details.collection_items[0].id == item.id
    assert details.collection_items[0].wearings == [wearing]


@pytest.mark.anyio
async def test_delete_perfume(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await create_perfume(
        session_factory,
        PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )

    await delete_perfume(session_factory, perfume.id)

    async with session_factory() as session:
        res = await session.scalars(select(PerfumeRow))
        assert res.all() == []

        perfume_row = await session.get(PerfumeRow, perfume.id)
        assert perfume_row is None


@pytest.mark.anyio
async def test_delete_perfume_not_found(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    with pytest.raises(PerfumeNotFoundError):
        await delete_perfume(session_factory, 999)


@pytest.mark.anyio
async def test_delete_perfume_with_active_collection_item_raises_conflict(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await create_perfume(
        session_factory,
        PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )
    await create_collection_item(
        session_factory,
        perfume_id=perfume.id,
        data=CollectionItemCreate(
            kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
        ),
    )

    details_before = await get_perfume_details(session_factory, perfume.id)

    with pytest.raises(PerfumeHasCollectionItemsError):
        await delete_perfume(session_factory, perfume.id)

    details_after = await get_perfume_details(session_factory, perfume.id)

    assert details_before == details_after


@pytest.mark.anyio
async def test_delete_perfume_with_archived_collection_item_raises_conflict(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await create_perfume(
        session_factory,
        PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )
    item = await create_collection_item(
        session_factory,
        perfume_id=perfume.id,
        data=CollectionItemCreate(
            kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
        ),
    )
    await set_collection_item_status(session_factory, item.id, "archived")

    details_before = await get_perfume_details(session_factory, perfume.id)

    with pytest.raises(PerfumeHasCollectionItemsError):
        await delete_perfume(session_factory, perfume.id)

    details_after = await get_perfume_details(session_factory, perfume.id)

    assert details_before == details_after


@pytest.mark.anyio
async def test_delete_wearing(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await create_perfume(
        session_factory,
        PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )
    item = await create_collection_item(
        session_factory,
        perfume_id=perfume.id,
        data=CollectionItemCreate(
            kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
        ),
    )

    wearing_to_delete = await create_wearing(
        session_factory,
        collection_item_id=item.id,
        data=WearingCreate(
            worn_at=datetime.fromisoformat("2026-10-02T09:30:00+03:00"),
            rating=6,
            comment="Test comment",
        ),
    )
    remaining_wearing = await create_wearing(
        session_factory,
        collection_item_id=item.id,
        data=WearingCreate(
            worn_at=datetime.fromisoformat("2026-09-02T09:30:00+03:00"),
            rating=10,
            comment="Test comment",
        ),
    )

    details_before = await get_perfume_details(session_factory, perfume.id)

    await delete_wearing(session_factory, wearing_to_delete.id)

    details_after = await get_perfume_details(session_factory, perfume.id)

    assert details_before.average_rating != details_after.average_rating
    assert details_after.average_rating == 10
    assert details_after.id == perfume.id
    assert len(details_after.collection_items) == 1
    assert details_after.collection_items[0].id == item.id
    assert details_after.collection_items[0].wearings == [remaining_wearing]


@pytest.mark.anyio
async def test_delete_wearing_with_archived_item(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await create_perfume(
        session_factory,
        PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )
    item = await create_collection_item(
        session_factory,
        perfume_id=perfume.id,
        data=CollectionItemCreate(
            kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
        ),
    )
    wearing = await create_wearing(
        session_factory,
        collection_item_id=item.id,
        data=WearingCreate(
            worn_at=datetime.fromisoformat("2026-10-02T09:30:00+03:00"),
            rating=6,
            comment="Test comment",
        ),
    )

    await set_collection_item_status(session_factory, item.id, "archived")

    await delete_wearing(session_factory, wearing.id)

    details = await get_perfume_details(session_factory, perfume.id)

    assert details.average_rating is None
    assert details.collection_items[0].wearings == []
    assert details.collection_items[0].status == "archived"


@pytest.mark.anyio
async def test_delete_wearing_not_found(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    with pytest.raises(WearingNotFoundError):
        await delete_wearing(session_factory, wearing_id=999)
