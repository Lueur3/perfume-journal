from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import perfume_journal.models as mdl
import perfume_journal.orm_models as orm
from perfume_journal.errors import (
    CollectionItemNotFoundError,
    DuplicatePerfumeError,
    PerfumeNotFoundError,
)
from perfume_journal.normalization import create_key


async def create_perfume(
    session_factory: async_sessionmaker[AsyncSession],
    data: mdl.PerfumeCreate,
) -> mdl.Perfume:
    brand_key = create_key(data.brand)
    name_key = create_key(data.name)
    concentration_key = create_key(data.concentration)

    orm_perfume = orm.Perfume(
        brand=data.brand,
        name=data.name,
        concentration=data.concentration,
        brand_key=brand_key,
        name_key=name_key,
        concentration_key=concentration_key,
    )

    try:
        async with session_factory.begin() as session:
            session.add(orm_perfume)
            await session.flush()

            mdl_perfume = mdl.Perfume(
                id=orm_perfume.id,
                brand=orm_perfume.brand,
                name=orm_perfume.name,
                concentration=orm_perfume.concentration,
            )

        return mdl_perfume

    except IntegrityError as exc:
        driver_error = exc.driver_exception
        sqlstate = getattr(driver_error, "sqlstate", None)
        constraint_name = getattr(driver_error, "constraint_name", None)

        if (
            sqlstate == "23505"
            and constraint_name == "uq_brand_name_concentration_keys"
        ):
            raise DuplicatePerfumeError("This perfume already exists.") from exc
        else:
            raise


async def get_perfume(
    session_factory: async_sessionmaker[AsyncSession],
    perfume_id: int,
) -> mdl.Perfume:
    async with session_factory() as session:
        result = await session.get(orm.Perfume, perfume_id)

        if result is None:
            raise PerfumeNotFoundError("Perfume not found.")

        return mdl.Perfume(
            id=result.id,
            brand=result.brand,
            name=result.name,
            concentration=result.concentration,
        )


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


async def create_wearing(
    session_factory: async_sessionmaker[AsyncSession],
    collection_item_id: int,
    data: mdl.WearingCreate,
) -> mdl.Wearing:
    async with session_factory.begin() as session:
        collection_item = await session.get(orm.CollectionItem, collection_item_id)

        if collection_item is None:
            raise CollectionItemNotFoundError("Collection item not found.")

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


async def get_perfume_details(
    session_factory: async_sessionmaker[AsyncSession],
    perfume_id: int,
) -> mdl.PerfumeDetails:

    async with session_factory() as session:
        orm_perfume = await session.get(orm.Perfume, perfume_id)
        if orm_perfume is None:
            raise PerfumeNotFoundError("Perfume not found.")

        statement_collection_item = select(orm.CollectionItem).where(
            orm.CollectionItem.perfume_id == perfume_id
        )
        result_collection_item_query = await session.execute(statement_collection_item)
        orm_collection_items = result_collection_item_query.scalars().all()

        collection_items_id = [item.id for item in orm_collection_items]

        statement_wering = select(orm.Wearing).where(
            orm.Wearing.collection_item_id.in_(collection_items_id)
        )
        result_wearing_query = await session.execute(statement_wering)
        orm_wearings = result_wearing_query.scalars().all()

    collection_items_details_list = []

    for item in orm_collection_items:
        wearing_list = []
        for wearing in orm_wearings:
            if wearing.collection_item_id == item.id:
                mdl_wearing = mdl.Wearing.model_validate(wearing, from_attributes=True)
                wearing_list.append(mdl_wearing)

        mdl_item = mdl.CollectionItem.model_validate(item, from_attributes=True)
        collection_items_details = mdl.CollectionItemDetails(
            **mdl_item.model_dump(), wearings=wearing_list
        )
        collection_items_details_list.append(collection_items_details)

    ratings = [
        wearing.rating
        for item in collection_items_details_list
        for wearing in item.wearings
        if wearing.rating is not None
    ]
    average_rating = sum(ratings) / len(ratings) if ratings else None

    mdl_perfume = mdl.Perfume.model_validate(orm_perfume, from_attributes=True)

    return mdl.PerfumeDetails(
        **mdl_perfume.model_dump(),
        collection_items=collection_items_details_list,
        average_rating=average_rating,
    )


async def update_perfume(
    session_factory: async_sessionmaker[AsyncSession],
    perfume_id: int,
    data: mdl.PerfumeCreate,
) -> mdl.Perfume:
    try:
        async with session_factory.begin() as session:
            perfume = await session.get(orm.Perfume, perfume_id)

            if perfume is None:
                raise PerfumeNotFoundError("Perfume not found.")

            for field in ("brand", "name", "concentration"):
                value = getattr(data, field)
                setattr(perfume, field, value)
                setattr(perfume, f"{field}_key", create_key(value))

            await session.flush()

            result = mdl.Perfume.model_validate(perfume, from_attributes=True)

        return result

    except IntegrityError as exc:
        driver_error = exc.driver_exception
        sqlstate = getattr(driver_error, "sqlstate", None)
        constraint_name = getattr(driver_error, "constraint_name", None)

        if (
            sqlstate == "23505"
            and constraint_name == "uq_brand_name_concentration_keys"
        ):
            raise DuplicatePerfumeError("This perfume already exists.") from exc
        else:
            raise
