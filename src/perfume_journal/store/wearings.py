from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import perfume_journal.models as mdl
import perfume_journal.orm_models as orm
from perfume_journal.errors import (
    CollectionItemArchivedError,
    CollectionItemNotFoundError,
    WearingNotFoundError,
)


async def create_wearing(
    session_factory: async_sessionmaker[AsyncSession],
    collection_item_id: int,
    data: mdl.WearingCreate,
) -> mdl.Wearing:
    async with session_factory.begin() as session:
        collection_item = await session.get(orm.CollectionItem, collection_item_id)

        if collection_item is None:
            raise CollectionItemNotFoundError("Collection item not found.")

        if collection_item.status == "archived":
            raise CollectionItemArchivedError(
                "Cannot add a wearing to an archived collection item."
            )

        orm_wearing = orm.Wearing(
            collection_item_id=collection_item_id,
            worn_at=data.worn_at,
            rating=data.rating,
            comment=data.comment,
        )

        session.add(orm_wearing)
        await session.flush()

        mdl_wearing = mdl.Wearing.model_validate(orm_wearing, from_attributes=True)

    return mdl_wearing


async def get_wearing(
    session_factory: async_sessionmaker[AsyncSession], wearing_id: int
) -> mdl.Wearing:
    async with session_factory() as session:
        wearing = await session.get(orm.Wearing, wearing_id)

        if wearing is None:
            raise WearingNotFoundError("Wearing not found.")

        return mdl.Wearing.model_validate(wearing, from_attributes=True)


async def list_wearings(
    session_factory: async_sessionmaker[AsyncSession],
    collection_item_id: int,
    worn_from: datetime | None = None,
    worn_before: datetime | None = None,
) -> list[mdl.Wearing]:
    async with session_factory() as session:
        collection_item = await session.get(orm.CollectionItem, collection_item_id)
        if collection_item is None:
            raise CollectionItemNotFoundError("Collection item not found.")

        stmt = (
            select(orm.Wearing)
            .where(orm.Wearing.collection_item_id == collection_item_id)
            .order_by(orm.Wearing.worn_at.desc())
        )
        if worn_from is not None:
            stmt = stmt.where(orm.Wearing.worn_at >= worn_from)
        if worn_before is not None:
            stmt = stmt.where(orm.Wearing.worn_at < worn_before)

        results = await session.scalars(stmt)

        return [
            mdl.Wearing.model_validate(item, from_attributes=True) for item in results
        ]


async def delete_wearing(
    session_factory: async_sessionmaker[AsyncSession], wearing_id: int
) -> None:
    async with session_factory.begin() as session:
        wearing = await session.get(orm.Wearing, wearing_id)

        if wearing is None:
            raise WearingNotFoundError("Wearing not found.")

        await session.delete(wearing)
        await session.flush()
