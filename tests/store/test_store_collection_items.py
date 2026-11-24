from datetime import date, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import perfume_journal.models as mdl
import perfume_journal.store.collection_items as item_store
import perfume_journal.store.perfumes as perfume_store
import perfume_journal.store.wearings as wearing_store
from perfume_journal.errors import (
    CollectionItemHasWearingsError,
    CollectionItemNotFoundError,
    PerfumeNotFoundError,
)
from perfume_journal.orm_models import CollectionItem as CollectionItemRow
from perfume_journal.orm_models import Perfume as PerfumeRow


@pytest.mark.anyio
async def test_create_collection_item(
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
    item_data = mdl.CollectionItemCreate(
        kind="sample", initial_volume_ml=2.0, acquired_on=date(2026, 10, 19)
    )

    with pytest.raises(PerfumeNotFoundError):
        await item_store.create_collection_item(
            session_factory, perfume_id=999, data=item_data
        )

    async with session_factory() as session:
        statement = select(CollectionItemRow)
        result = await session.execute(statement)
        assert result.scalar_one_or_none() is None


@pytest.mark.anyio
async def test_create_multiple_identical_collection_items(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await perfume_store.create_perfume(
        session_factory,
        mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDP"),
    )
    item_data = mdl.CollectionItemCreate(kind="sample")
    first_item = await item_store.create_collection_item(
        session_factory, perfume_id=perfume.id, data=item_data
    )
    second_item = await item_store.create_collection_item(
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
async def test_archive_and_restore_collection_item(
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
    wearing = await wearing_store.create_wearing(
        session_factory,
        collection_item_id=item.id,
        data=mdl.WearingCreate(
            worn_at=datetime.fromisoformat("2026-10-02T09:30:00+03:00"),
            rating=10,
            comment="Test comment",
        ),
    )

    archived_item = await item_store.set_collection_item_status(
        session_factory, item.id, "archived"
    )
    assert archived_item.status == "archived"
    assert archived_item.id == item.id
    assert archived_item.perfume_id == perfume.id

    details_archived = await perfume_store.get_perfume_details(
        session_factory, perfume_id=perfume.id
    )
    assert len(details_archived.collection_items) == 1
    item_archived = details_archived.collection_items[0]
    assert item_archived.id == item.id
    assert item_archived.status == "archived"
    assert item_archived.wearings == [wearing]

    archived_item_repeat = await item_store.set_collection_item_status(
        session_factory, item.id, "archived"
    )
    assert archived_item_repeat == archived_item

    active_item = await item_store.set_collection_item_status(
        session_factory, item.id, "active"
    )
    assert active_item == item

    details_active = await perfume_store.get_perfume_details(
        session_factory, perfume_id=perfume.id
    )
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
        await item_store.set_collection_item_status(
            session_factory, collection_item_id=999, status="archived"
        )


@pytest.mark.anyio
async def test_list_collection_items_empty(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    assert await item_store.list_collection_items(session_factory, "active") == []


@pytest.mark.anyio
async def test_list_collection_items_filters_by_status(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await perfume_store.create_perfume(
        session_factory,
        mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )
    first_item = await item_store.create_collection_item(
        session_factory,
        perfume_id=perfume.id,
        data=mdl.CollectionItemCreate(
            kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
        ),
    )
    second_item = await item_store.create_collection_item(
        session_factory,
        perfume_id=perfume.id,
        data=mdl.CollectionItemCreate(
            kind="bottle", initial_volume_ml=200, acquired_on=date(2026, 9, 20)
        ),
    )

    archived_item = await item_store.set_collection_item_status(
        session_factory, second_item.id, "archived"
    )

    assert await item_store.list_collection_items(session_factory, "active") == [
        first_item
    ]
    assert await item_store.list_collection_items(session_factory, "archived") == [
        archived_item
    ]


@pytest.mark.anyio
async def test_delete_active_collection_item(
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

    await item_store.delete_collection_item(session_factory, item.id)

    async with session_factory() as session:
        res = await session.scalars(select(CollectionItemRow))
        assert res.all() == []

        perfume_row = await session.get(PerfumeRow, perfume.id)
        assert perfume_row is not None


@pytest.mark.anyio
async def test_delete_archived_collection_item(
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
    archived_item = await item_store.set_collection_item_status(
        session_factory, item.id, "archived"
    )

    await item_store.delete_collection_item(session_factory, archived_item.id)

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
        await item_store.delete_collection_item(session_factory, collection_item_id=999)


@pytest.mark.anyio
async def test_delete_collection_item_with_wearings_raises_conflict(
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
        item.id,
        mdl.WearingCreate(
            worn_at=datetime.fromisoformat("2026-10-02T15:00:00+03:00"),
            rating=9,
        ),
    )

    with pytest.raises(CollectionItemHasWearingsError):
        await item_store.delete_collection_item(session_factory, item.id)

    details = await perfume_store.get_perfume_details(session_factory, perfume.id)

    assert details.collection_items[0].id == item.id
    assert details.collection_items[0].wearings == [wearing]


@pytest.mark.anyio
async def test_get_collection_item_by_id(
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

    target_item = await item_store.get_collection_item(session_factory, item.id)

    assert item == target_item


@pytest.mark.anyio
async def test_get_collection_item_archived_by_id(
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

    archived_item = await item_store.set_collection_item_status(
        session_factory, item.id, "archived"
    )

    target_item = await item_store.get_collection_item(
        session_factory, archived_item.id
    )

    assert archived_item == target_item


@pytest.mark.anyio
async def test_get_collection_item_not_found(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    with pytest.raises(CollectionItemNotFoundError):
        await item_store.get_collection_item(session_factory, collection_item_id=999)
