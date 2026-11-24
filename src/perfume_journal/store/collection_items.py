from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import perfume_journal.models as mdl
import perfume_journal.orm_models as orm
from perfume_journal.errors import (
    CollectionItemHasWearingsError,
    CollectionItemNotFoundError,
    PerfumeNotFoundError,
)
from perfume_journal.sqlalchemy_store import matches_integrity_error


async def create_collection_item(
    session_factory: async_sessionmaker[AsyncSession],
    perfume_id: int,
    data: mdl.CollectionItemCreate,
) -> mdl.CollectionItem:
    async with session_factory.begin() as session:
        perfume = await session.get(orm.Perfume, perfume_id)

        if perfume is None:
            raise PerfumeNotFoundError("Perfume not found.")

        orm_collection_item = orm.CollectionItem(
            perfume_id=perfume_id,
            kind=data.kind,
            initial_volume_ml=data.initial_volume_ml,
            acquired_on=data.acquired_on,
        )
        session.add(orm_collection_item)
        await session.flush()

        mdl_collection_item = mdl.CollectionItem.model_validate(
            orm_collection_item, from_attributes=True
        )

    return mdl_collection_item


async def get_collection_item(
    session_factory: async_sessionmaker[AsyncSession],
    collection_item_id: int,
) -> mdl.CollectionItem:
    async with session_factory() as session:
        collection_item = await session.get(orm.CollectionItem, collection_item_id)

        if collection_item is None:
            raise CollectionItemNotFoundError("Collection item not found.")

    return mdl.CollectionItem.model_validate(collection_item, from_attributes=True)


async def list_collection_items(
    session_factory: async_sessionmaker[AsyncSession],
    status: mdl.CollectionItemStatus,
) -> list[mdl.CollectionItem]:
    async with session_factory() as session:
        results = await session.scalars(
            select(orm.CollectionItem)
            .where(orm.CollectionItem.status == status)
            .order_by(orm.CollectionItem.id)
        )

        return [
            mdl.CollectionItem.model_validate(item, from_attributes=True)
            for item in results
        ]


async def set_collection_item_status(
    session_factory: async_sessionmaker[AsyncSession],
    collection_item_id: int,
    status: mdl.CollectionItemStatus,
) -> mdl.CollectionItem:
    async with session_factory.begin() as session:
        item = await session.get(orm.CollectionItem, collection_item_id)

        if item is None:
            raise CollectionItemNotFoundError("Collection item not found.")

        item.status = status
        await session.flush()

        mdl_item = mdl.CollectionItem.model_validate(item, from_attributes=True)

    return mdl_item


async def delete_collection_item(
    session_factory: async_sessionmaker[AsyncSession],
    collection_item_id: int,
) -> None:
    try:
        async with session_factory.begin() as session:
            collection_item = await session.get(orm.CollectionItem, collection_item_id)

            if collection_item is None:
                raise CollectionItemNotFoundError("Collection item not found.")

            await session.delete(collection_item)
            await session.flush()

    except IntegrityError as exc:
        if matches_integrity_error(exc, "23001", "wearings_collection_item_id_fkey"):
            raise CollectionItemHasWearingsError(
                "Cannot delete a collection item with wearing history."
            ) from exc
        else:
            raise
