from datetime import date, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import perfume_journal.models as mdl
import perfume_journal.store.collection_items as item_store
import perfume_journal.store.perfumes as perfume_store
import perfume_journal.store.wearings as wearing_store
from perfume_journal.errors import (
    DuplicatePerfumeError,
    PerfumeHasCollectionItemsError,
    PerfumeNotFoundError,
)
from perfume_journal.orm_models import Perfume as PerfumeRow


@pytest.mark.anyio
async def test_create_perfume(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    data = mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDP")
    perfume = await perfume_store.create_perfume(session_factory, data)

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
    data = mdl.PerfumeCreate(
        brand="Tom Ford", name="Oud Wood", concentration=concentration
    )
    perfume = await perfume_store.create_perfume(session_factory, data)

    duplicate_data = mdl.PerfumeCreate(
        brand="tom   ford", name="OUD  WOOD", concentration=concentration
    )
    with pytest.raises(DuplicatePerfumeError):
        await perfume_store.create_perfume(session_factory, duplicate_data)

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
    first_data = mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")
    first_perfume = await perfume_store.create_perfume(session_factory, first_data)

    second_data = mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDP")
    second_perfume = await perfume_store.create_perfume(session_factory, second_data)

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

    monkeypatch.setattr(perfume_store, "create_key", broken_key)

    data = mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDP")

    with pytest.raises(IntegrityError) as caught:
        await perfume_store.create_perfume(session_factory, data)

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
    first_data = mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDP")
    await perfume_store.create_perfume(session_factory, first_data)
    target_data = mdl.PerfumeCreate(
        brand="Tom Ford", name="Oud Wood", concentration="EDT"
    )
    target_perfume = await perfume_store.create_perfume(session_factory, target_data)

    result = await perfume_store.get_perfume(session_factory, target_perfume.id)

    assert result == target_perfume


@pytest.mark.anyio
async def test_get_perfume_not_found(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    with pytest.raises(PerfumeNotFoundError):
        await perfume_store.get_perfume(session_factory, perfume_id=999)


@pytest.mark.anyio
async def test_get_perfume_details_includes_wearings_and_average_rating(
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

    first_wearing = await wearing_store.create_wearing(
        session_factory,
        collection_item_id=first_item.id,
        data=mdl.WearingCreate(
            worn_at=datetime.fromisoformat("2026-10-02T09:30:00+03:00"),
            rating=10,
            comment="Test comment",
        ),
    )
    second_wearing = await wearing_store.create_wearing(
        session_factory,
        collection_item_id=first_item.id,
        data=mdl.WearingCreate(
            worn_at=datetime.fromisoformat("2026-10-02T09:30:00+03:00"),
            rating=8,
            comment="Test comment",
        ),
    )
    third_wearing = await wearing_store.create_wearing(
        session_factory,
        collection_item_id=second_item.id,
        data=mdl.WearingCreate(
            worn_at=datetime.fromisoformat("2026-10-02T09:30:00+03:00"),
            rating=4,
            comment="Test comment",
        ),
    )
    fourth_wearing = await wearing_store.create_wearing(
        session_factory,
        collection_item_id=second_item.id,
        data=mdl.WearingCreate(
            worn_at=datetime.fromisoformat("2026-10-02T09:30:00+03:00"),
        ),
    )

    details = await perfume_store.get_perfume_details(
        session_factory, perfume_id=perfume.id
    )

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
    perfume = await perfume_store.create_perfume(
        session_factory,
        mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )

    details = await perfume_store.get_perfume_details(
        session_factory, perfume_id=perfume.id
    )

    assert details.id == perfume.id
    assert details.collection_items == []
    assert details.average_rating is None


@pytest.mark.anyio
async def test_get_perfume_details_not_found(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    with pytest.raises(PerfumeNotFoundError):
        await perfume_store.get_perfume_details(session_factory, perfume_id=999)


@pytest.mark.anyio
async def test_get_perfume_details_without_ratings(
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
    wearing = await wearing_store.create_wearing(
        session_factory,
        second_item.id,
        mdl.WearingCreate(
            worn_at=datetime.fromisoformat("2026-10-02T09:30:00+03:00"),
        ),
    )

    details = await perfume_store.get_perfume_details(session_factory, perfume.id)

    assert details.average_rating is None
    assert len(details.collection_items) == 2

    items_by_id = {item.id: item for item in details.collection_items}
    assert items_by_id[first_item.id].wearings == []
    assert items_by_id[second_item.id].wearings == [wearing]


@pytest.mark.anyio
async def test_perfume_details_isolation(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    first_perfume = await perfume_store.create_perfume(
        session_factory,
        mdl.PerfumeCreate(brand="Dior", name="Sauvage", concentration="EDT"),
    )
    first_item = await item_store.create_collection_item(
        session_factory,
        perfume_id=first_perfume.id,
        data=mdl.CollectionItemCreate(kind="bottle", initial_volume_ml=100),
    )
    await wearing_store.create_wearing(
        session_factory,
        first_item.id,
        mdl.WearingCreate(
            worn_at=datetime.fromisoformat("2026-10-01T12:00:00+03:00"),
            rating=2,
        ),
    )

    second_perfume = await perfume_store.create_perfume(
        session_factory,
        mdl.PerfumeCreate(brand="Chanel", name="Bleu de Chanel", concentration="EDP"),
    )
    second_item = await item_store.create_collection_item(
        session_factory,
        perfume_id=second_perfume.id,
        data=mdl.CollectionItemCreate(kind="sample", initial_volume_ml=10),
    )
    second_wearing = await wearing_store.create_wearing(
        session_factory,
        second_item.id,
        mdl.WearingCreate(
            worn_at=datetime.fromisoformat("2026-10-02T15:00:00+03:00"),
            rating=9,
        ),
    )

    details = await perfume_store.get_perfume_details(
        session_factory, second_perfume.id
    )

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
    original_perfume = await perfume_store.create_perfume(
        session_factory,
        mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )

    update_data = mdl.PerfumeCreate(brand="Tom Ford", name="Oud Wood")
    updated_perfume = await perfume_store.update_perfume(
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
    existing_perfume = await perfume_store.create_perfume(
        session_factory, mdl.PerfumeCreate(brand="Tom Ford", name="Oud Wood")
    )
    target_perfume = await perfume_store.create_perfume(
        session_factory, mdl.PerfumeCreate(brand="Creed", name="Aventus")
    )

    duplicate_data = mdl.PerfumeCreate(brand="tom  ford", name="oud   wood")

    with pytest.raises(DuplicatePerfumeError):
        await perfume_store.update_perfume(
            session_factory, target_perfume.id, duplicate_data
        )

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
    data = mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")

    with pytest.raises(PerfumeNotFoundError):
        await perfume_store.update_perfume(session_factory, perfume_id=999, data=data)

    async with session_factory() as session:
        statement = select(PerfumeRow)
        result = await session.execute(statement)
        assert result.scalar_one_or_none() is None


@pytest.mark.anyio
async def test_list_perfumes_empty(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    assert await perfume_store.list_perfumes(session_factory) == []


@pytest.mark.anyio
async def test_list_perfumes(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    first_perfume = await perfume_store.create_perfume(
        session_factory,
        mdl.PerfumeCreate(brand="Tom Ford", name="Oud Wood", concentration="EDT"),
    )
    second_perfume = await perfume_store.create_perfume(
        session_factory, mdl.PerfumeCreate(brand="Creed", name="Aventus")
    )

    perfumes = await perfume_store.list_perfumes(session_factory)

    assert perfumes == [first_perfume, second_perfume]


@pytest.mark.anyio
async def test_list_perfumes_search(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    first_perfume = await perfume_store.create_perfume(
        session_factory,
        mdl.PerfumeCreate(brand="Tom Ford", name="Oud Wood", concentration="EDT"),
    )
    second_perfume = await perfume_store.create_perfume(
        session_factory, mdl.PerfumeCreate(brand="Creed", name="Aventus")
    )
    await perfume_store.create_perfume(
        session_factory, mdl.PerfumeCreate(brand="Chanel", name="Bleu de Chanel")
    )

    find_perfume_1 = await perfume_store.list_perfumes(session_factory, q="ford")
    find_perfume_2 = await perfume_store.list_perfumes(session_factory, q="AVEN  ")

    assert find_perfume_1 == [first_perfume]
    assert find_perfume_2 == [second_perfume]


@pytest.mark.anyio
async def test_list_perfumes_search_no_matches(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await perfume_store.create_perfume(
        session_factory,
        mdl.PerfumeCreate(brand="Tom Ford", name="Oud Wood", concentration="EDT"),
    )

    assert await perfume_store.list_perfumes(session_factory, q="Dior") == []


@pytest.mark.anyio
async def test_delete_perfume(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await perfume_store.create_perfume(
        session_factory,
        mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )

    await perfume_store.delete_perfume(session_factory, perfume.id)

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
        await perfume_store.delete_perfume(session_factory, 999)


@pytest.mark.anyio
async def test_delete_perfume_with_active_collection_item_raises_conflict(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await perfume_store.create_perfume(
        session_factory,
        mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )
    await item_store.create_collection_item(
        session_factory,
        perfume_id=perfume.id,
        data=mdl.CollectionItemCreate(
            kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
        ),
    )

    details_before = await perfume_store.get_perfume_details(
        session_factory, perfume.id
    )

    with pytest.raises(PerfumeHasCollectionItemsError):
        await perfume_store.delete_perfume(session_factory, perfume.id)

    details_after = await perfume_store.get_perfume_details(session_factory, perfume.id)

    assert details_before == details_after


@pytest.mark.anyio
async def test_delete_perfume_with_archived_collection_item_raises_conflict(
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
    await item_store.update_collection_item(
        session_factory, item.id, mdl.CollectionItemUpdate(status="archived")
    )

    details_before = await perfume_store.get_perfume_details(
        session_factory, perfume.id
    )

    with pytest.raises(PerfumeHasCollectionItemsError):
        await perfume_store.delete_perfume(session_factory, perfume.id)

    details_after = await perfume_store.get_perfume_details(session_factory, perfume.id)

    assert details_before == details_after


@pytest.mark.anyio
async def test_update_perfume_source_partial_update_preserves_other_fields(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await perfume_store.create_perfume(
        session_factory,
        mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )

    async with session_factory.begin() as session:
        stmt = select(PerfumeRow).where(PerfumeRow.id == perfume.id)
        res_query = await session.execute(stmt)
        row = res_query.scalar_one()
        row.source_sillage = "arms_length"
        row.source_url = "https://example.com"

    new_data = mdl.PerfumeSourceUpdate(sillage="fills_room")

    new_source = await perfume_store.update_perfume_source(
        session_factory, perfume.id, data=new_data
    )

    assert new_source.sillage == "fills_room"
    assert new_source.url == "https://example.com"

    async with session_factory() as session:
        stmt = select(PerfumeRow)
        res_query = await session.execute(stmt)
        updated_perfume = res_query.scalar_one()

        assert updated_perfume.brand == "Creed"
        assert updated_perfume.name == "Aventus"
        assert updated_perfume.concentration == "EDT"
        assert updated_perfume.source_sillage == "fills_room"
        assert updated_perfume.source_url == "https://example.com"


@pytest.mark.anyio
async def test_update_perfume_source_none_clears_field(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await perfume_store.create_perfume(
        session_factory,
        mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )

    async with session_factory.begin() as session:
        stmt = select(PerfumeRow).where(PerfumeRow.id == perfume.id)
        res_query = await session.execute(stmt)
        row = res_query.scalar_one()
        row.source_sillage = "arms_length"
        row.source_url = "https://example.com"

    new_source = await perfume_store.update_perfume_source(
        session_factory, perfume.id, data=mdl.PerfumeSourceUpdate(url=None)
    )
    assert new_source.url is None
    assert new_source.sillage == "arms_length"

    async with session_factory() as session:
        stmt = select(PerfumeRow)
        res_query = await session.execute(stmt)
        updated_perfume = res_query.scalar_one()

        assert updated_perfume.brand == "Creed"
        assert updated_perfume.name == "Aventus"
        assert updated_perfume.concentration == "EDT"
        assert updated_perfume.source_sillage == "arms_length"
        assert updated_perfume.source_url is None


@pytest.mark.anyio
async def test_update_perfume_source_empty_payload_preserves_all_fields(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await perfume_store.create_perfume(
        session_factory,
        mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )

    async with session_factory.begin() as session:
        stmt = select(PerfumeRow).where(PerfumeRow.id == perfume.id)
        res_query = await session.execute(stmt)
        row = res_query.scalar_one()
        row.source_sillage = "arms_length"
        row.source_url = "https://example.com"

    new_source = await perfume_store.update_perfume_source(
        session_factory, perfume.id, data=mdl.PerfumeSourceUpdate()
    )

    assert new_source.sillage == "arms_length"
    assert new_source.url == "https://example.com"

    async with session_factory() as session:
        stmt = select(PerfumeRow)
        res_query = await session.execute(stmt)
        updated_perfume = res_query.scalar_one()

        assert updated_perfume.brand == "Creed"
        assert updated_perfume.name == "Aventus"
        assert updated_perfume.concentration == "EDT"
        assert updated_perfume.source_sillage == "arms_length"
        assert updated_perfume.source_url == "https://example.com"


@pytest.mark.anyio
async def test_update_perfume_source_missing_perfume_raises_not_found(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    with pytest.raises(PerfumeNotFoundError):
        await perfume_store.update_perfume_source(
            session_factory, perfume_id=999, data=mdl.PerfumeSourceUpdate()
        )


@pytest.mark.anyio
async def test_update_perfume_personal_partial_update_preserves_other_fields(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await perfume_store.create_perfume(
        session_factory,
        mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )

    async with session_factory.begin() as session:
        stmt = select(PerfumeRow).where(PerfumeRow.id == perfume.id)
        res_query = await session.execute(stmt)
        row = res_query.scalar_one()
        row.personal_sillage = "arms_length"
        row.personal_longevity_hours = 6.5
        row.personal_comment = "Great scent"

    new_data = mdl.PerfumePersonalUpdate(sillage="fills_room")

    new_personal = await perfume_store.update_perfume_personal(
        session_factory, perfume.id, data=new_data
    )

    assert new_personal.sillage == "fills_room"
    assert new_personal.longevity_hours == 6.5
    assert new_personal.comment == "Great scent"

    async with session_factory() as session:
        stmt = select(PerfumeRow).where(PerfumeRow.id == perfume.id)
        res_query = await session.execute(stmt)
        updated_perfume = res_query.scalar_one()

        assert updated_perfume.brand == "Creed"
        assert updated_perfume.name == "Aventus"
        assert updated_perfume.concentration == "EDT"
        assert updated_perfume.personal_sillage == "fills_room"
        assert updated_perfume.personal_longevity_hours == 6.5
        assert updated_perfume.personal_comment == "Great scent"


@pytest.mark.anyio
async def test_update_perfume_personal_none_clears_field(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await perfume_store.create_perfume(
        session_factory,
        mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )

    async with session_factory.begin() as session:
        stmt = select(PerfumeRow).where(PerfumeRow.id == perfume.id)
        res_query = await session.execute(stmt)
        row = res_query.scalar_one()
        row.personal_sillage = "arms_length"
        row.personal_comment = "Temporary comment"

    new_personal = await perfume_store.update_perfume_personal(
        session_factory, perfume.id, data=mdl.PerfumePersonalUpdate(comment=None)
    )
    assert new_personal.comment is None
    assert new_personal.sillage == "arms_length"

    async with session_factory() as session:
        stmt = select(PerfumeRow).where(PerfumeRow.id == perfume.id)
        res_query = await session.execute(stmt)
        updated_perfume = res_query.scalar_one()

        assert updated_perfume.brand == "Creed"
        assert updated_perfume.name == "Aventus"
        assert updated_perfume.concentration == "EDT"
        assert updated_perfume.personal_sillage == "arms_length"
        assert updated_perfume.personal_comment is None


@pytest.mark.anyio
async def test_update_perfume_personal_empty_payload_preserves_all_fields(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    perfume = await perfume_store.create_perfume(
        session_factory,
        mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT"),
    )

    async with session_factory.begin() as session:
        stmt = select(PerfumeRow).where(PerfumeRow.id == perfume.id)
        res_query = await session.execute(stmt)
        row = res_query.scalar_one()
        row.personal_sillage = "arms_length"
        row.personal_longevity_hours = 6.5

    new_personal = await perfume_store.update_perfume_personal(
        session_factory, perfume.id, data=mdl.PerfumePersonalUpdate()
    )

    assert new_personal.sillage == "arms_length"
    assert new_personal.longevity_hours == 6.5

    async with session_factory() as session:
        stmt = select(PerfumeRow).where(PerfumeRow.id == perfume.id)
        res_query = await session.execute(stmt)
        updated_perfume = res_query.scalar_one()

        assert updated_perfume.brand == "Creed"
        assert updated_perfume.name == "Aventus"
        assert updated_perfume.concentration == "EDT"
        assert updated_perfume.personal_sillage == "arms_length"
        assert updated_perfume.personal_longevity_hours == 6.5


@pytest.mark.anyio
async def test_update_perfume_personal_missing_perfume_raises_not_found(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    with pytest.raises(PerfumeNotFoundError):
        await perfume_store.update_perfume_personal(
            session_factory, perfume_id=999, data=mdl.PerfumePersonalUpdate()
        )
