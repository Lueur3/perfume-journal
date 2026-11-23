from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import perfume_journal.models as mdl
import perfume_journal.store.collection_items as item_store
import perfume_journal.store.perfumes as perfume_store
import perfume_journal.store.wearings as wearing_store
from perfume_journal.errors import (
    CollectionItemArchivedError,
    CollectionItemNotFoundError,
    WearingNotFoundError,
)
from perfume_journal.orm_models import Wearing as WearingRow


@pytest.mark.anyio
async def test_create_wearing(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await perfume_store.create_perfume(
        session_factory,
        mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDP"),
    )
    item_data = mdl.CollectionItemCreate(
        kind="sample", initial_volume_ml=2.0, acquired_on=date(2026, 10, 19)
    )
    item = await item_store.create_collection_item(
        session_factory, perfume.id, item_data
    )

    expected_worn_at = datetime(
        2026, 10, 2, 9, 30, 0, tzinfo=timezone(timedelta(hours=3))
    )
    wearing_data = mdl.WearingCreate(
        worn_at=expected_worn_at,
        rating=7,
        comment="Test comment",
    )
    wearing = await wearing_store.create_wearing(
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
    wearing_data = mdl.WearingCreate(
        worn_at=datetime.fromisoformat("2026-10-02T09:30:00+03:00"),
        rating=7,
        comment="Test comment",
    )

    with pytest.raises(CollectionItemNotFoundError):
        await wearing_store.create_wearing(
            session_factory, collection_item_id=999, data=wearing_data
        )

    async with session_factory() as session:
        statement = select(WearingRow)
        result = await session.execute(statement)
        assert result.scalar_one_or_none() is None


@pytest.mark.anyio
async def test_create_multiple_identical_wearings(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await perfume_store.create_perfume(
        session_factory,
        mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDP"),
    )
    item_data = mdl.CollectionItemCreate(kind="sample")
    item = await item_store.create_collection_item(
        session_factory, perfume_id=perfume.id, data=item_data
    )

    expected_worn_at = datetime.fromisoformat("2026-10-02T09:30:00+03:00")
    wearing_data = mdl.WearingCreate(worn_at=expected_worn_at)
    first_wearing = await wearing_store.create_wearing(
        session_factory, collection_item_id=item.id, data=wearing_data
    )
    second_wearing = await wearing_store.create_wearing(
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
async def test_create_wearing_for_archived_item_raises_conflict(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await perfume_store.create_perfume(
        session_factory,
        mdl.PerfumeCreate(brand="Tom Ford", name="Oud Wood", concentration="EDT"),
    )
    item = await item_store.create_collection_item(
        session_factory,
        perfume_id=perfume.id,
        data=mdl.CollectionItemCreate(
            kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
        ),
    )
    await item_store.set_collection_item_status(session_factory, item.id, "archived")

    wearing_data = mdl.WearingCreate(
        worn_at=datetime.fromisoformat("2026-10-02T09:30:00+03:00"),
        rating=10,
        comment="Test comment",
    )

    with pytest.raises(CollectionItemArchivedError):
        await wearing_store.create_wearing(
            session_factory,
            collection_item_id=item.id,
            data=wearing_data,
        )

    details_archived = await perfume_store.get_perfume_details(
        session_factory, perfume_id=perfume.id
    )
    assert len(details_archived.collection_items) == 1
    item_archived = details_archived.collection_items[0]
    assert item_archived.id == item.id
    assert item_archived.status == "archived"
    assert item_archived.wearings == []

    await item_store.set_collection_item_status(session_factory, item.id, "active")

    wearing = await wearing_store.create_wearing(
        session_factory,
        collection_item_id=item.id,
        data=wearing_data,
    )

    details_active = await perfume_store.get_perfume_details(
        session_factory, perfume_id=perfume.id
    )
    assert len(details_active.collection_items) == 1
    item_active = details_active.collection_items[0]
    assert item_active.id == item.id
    assert item_active.status == "active"
    assert item_active.wearings == [wearing]


@pytest.mark.anyio
async def test_list_wearings_returns_item_history_newest_first(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await perfume_store.create_perfume(
        session_factory,
        mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )
    item = await item_store.create_collection_item(
        session_factory,
        perfume_id=perfume.id,
        data=mdl.CollectionItemCreate(
            kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
        ),
    )
    other_item = await item_store.create_collection_item(
        session_factory,
        perfume_id=perfume.id,
        data=mdl.CollectionItemCreate(
            kind="bottle", initial_volume_ml=150, acquired_on=date(2026, 9, 15)
        ),
    )

    older_wearing = await wearing_store.create_wearing(
        session_factory,
        item.id,
        mdl.WearingCreate(
            worn_at=datetime.fromisoformat("2026-10-28T15:00:00+03:00"),
            rating=9,
        ),
    )
    newer_wearing = await wearing_store.create_wearing(
        session_factory,
        item.id,
        mdl.WearingCreate(
            worn_at=datetime.fromisoformat("2026-11-05T15:00:00+03:00"),
            rating=9,
        ),
    )
    await wearing_store.create_wearing(
        session_factory,
        other_item.id,
        mdl.WearingCreate(
            worn_at=datetime.fromisoformat("2026-10-15T15:00:00+03:00"),
            rating=9,
        ),
    )

    wearings = await wearing_store.list_wearings(session_factory, item.id)

    assert wearings == [newer_wearing, older_wearing]


@pytest.mark.anyio
async def test_list_wearings_empty(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await perfume_store.create_perfume(
        session_factory,
        mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )
    item = await item_store.create_collection_item(
        session_factory,
        perfume_id=perfume.id,
        data=mdl.CollectionItemCreate(
            kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
        ),
    )

    assert await wearing_store.list_wearings(session_factory, item.id) == []


@pytest.mark.anyio
async def test_list_wearings_not_found(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    with pytest.raises(CollectionItemNotFoundError):
        await wearing_store.list_wearings(session_factory, collection_item_id=999)


@pytest.mark.anyio
async def test_list_wearings_filter_by_date_range(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await perfume_store.create_perfume(
        session_factory,
        mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )
    item = await item_store.create_collection_item(
        session_factory,
        perfume_id=perfume.id,
        data=mdl.CollectionItemCreate(
            kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
        ),
    )

    wearing_lower = await wearing_store.create_wearing(
        session_factory,
        item.id,
        mdl.WearingCreate(
            worn_at=datetime.fromisoformat("2026-10-28T10:00:00+03:00"),
            rating=9,
        ),
    )
    wearing_middle = await wearing_store.create_wearing(
        session_factory,
        item.id,
        mdl.WearingCreate(
            worn_at=datetime.fromisoformat("2026-11-01T12:00:00+03:00"),
            rating=9,
        ),
    )
    await wearing_store.create_wearing(
        session_factory,
        item.id,
        mdl.WearingCreate(
            worn_at=datetime.fromisoformat("2026-11-05T10:00:00+03:00"),
            rating=9,
        ),
    )

    t_zone = timezone(timedelta(hours=3))
    worn_from = datetime(2026, 10, 28, 10, 0, tzinfo=t_zone)
    worn_before = datetime(2026, 11, 5, 10, 0, tzinfo=t_zone)

    wearings = await wearing_store.list_wearings(
        session_factory,
        item.id,
        worn_from=worn_from,
        worn_before=worn_before,
    )

    assert wearings == [wearing_middle, wearing_lower]


@pytest.mark.anyio
async def test_delete_wearing(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await perfume_store.create_perfume(
        session_factory,
        mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )
    item = await item_store.create_collection_item(
        session_factory,
        perfume_id=perfume.id,
        data=mdl.CollectionItemCreate(
            kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
        ),
    )

    wearing_to_delete = await wearing_store.create_wearing(
        session_factory,
        collection_item_id=item.id,
        data=mdl.WearingCreate(
            worn_at=datetime.fromisoformat("2026-10-02T09:30:00+03:00"),
            rating=6,
            comment="Test comment",
        ),
    )
    remaining_wearing = await wearing_store.create_wearing(
        session_factory,
        collection_item_id=item.id,
        data=mdl.WearingCreate(
            worn_at=datetime.fromisoformat("2026-09-02T09:30:00+03:00"),
            rating=10,
            comment="Test comment",
        ),
    )

    details_before = await perfume_store.get_perfume_details(
        session_factory, perfume.id
    )

    await wearing_store.delete_wearing(session_factory, wearing_to_delete.id)

    details_after = await perfume_store.get_perfume_details(session_factory, perfume.id)

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
    perfume = await perfume_store.create_perfume(
        session_factory,
        mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )
    item = await item_store.create_collection_item(
        session_factory,
        perfume_id=perfume.id,
        data=mdl.CollectionItemCreate(
            kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
        ),
    )
    wearing = await wearing_store.create_wearing(
        session_factory,
        collection_item_id=item.id,
        data=mdl.WearingCreate(
            worn_at=datetime.fromisoformat("2026-10-02T09:30:00+03:00"),
            rating=6,
            comment="Test comment",
        ),
    )

    await item_store.set_collection_item_status(session_factory, item.id, "archived")

    await wearing_store.delete_wearing(session_factory, wearing.id)

    details = await perfume_store.get_perfume_details(session_factory, perfume.id)

    assert details.average_rating is None
    assert details.collection_items[0].wearings == []
    assert details.collection_items[0].status == "archived"


@pytest.mark.anyio
async def test_delete_wearing_not_found(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    with pytest.raises(WearingNotFoundError):
        await wearing_store.delete_wearing(session_factory, wearing_id=999)
