from collections import defaultdict

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import perfume_journal.models as mdl
import perfume_journal.orm_models as orm
from perfume_journal.errors import (
    DuplicatePerfumeError,
    PerfumeHasCollectionItemsError,
    PerfumeNotFoundError,
)
from perfume_journal.normalization import create_key
from perfume_journal.sqlalchemy_store import matches_integrity_error


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
        if matches_integrity_error(exc, "23505", "uq_brand_name_concentration_keys"):
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


async def get_perfume_details(
    session_factory: async_sessionmaker[AsyncSession],
    perfume_id: int,
) -> mdl.PerfumeDetails:

    async with session_factory() as session:
        orm_perfume = await session.get(orm.Perfume, perfume_id)
        if orm_perfume is None:
            raise PerfumeNotFoundError("Perfume not found.")

        source = mdl.PerfumeSource.model_validate(
            {
                "sillage": orm_perfume.source_sillage,
                "longevity": orm_perfume.source_longevity,
                "seasons": orm_perfume.source_seasons,
                "times_of_day": orm_perfume.source_times_of_day,
                "url": orm_perfume.source_url,
            }
        )

        personal = mdl.PerfumePersonal.model_validate(
            {
                "sillage": orm_perfume.personal_sillage,
                "longevity": orm_perfume.personal_longevity,
                "longevity_hours": orm_perfume.personal_longevity_hours,
                "seasons": orm_perfume.personal_seasons,
                "times_of_day": orm_perfume.personal_times_of_day,
                "comment": orm_perfume.personal_comment,
            }
        )

        statement_collection_item = select(orm.CollectionItem).where(
            orm.CollectionItem.perfume_id == perfume_id
        )
        result_collection_item_query = await session.execute(statement_collection_item)
        orm_collection_items = result_collection_item_query.scalars().all()

        collection_items_id = [item.id for item in orm_collection_items]

        statement_wearing = select(orm.Wearing).where(
            orm.Wearing.collection_item_id.in_(collection_items_id)
        )
        result_wearing_query = await session.execute(statement_wearing)
        orm_wearings = result_wearing_query.scalars().all()

    wearings_by_items_id: dict[int, list[mdl.Wearing]] = defaultdict(list)
    for wearing in orm_wearings:
        wearings_by_items_id[wearing.collection_item_id].append(
            mdl.Wearing.model_validate(wearing, from_attributes=True)
        )

    collection_items_details_list = []

    for item in orm_collection_items:
        wearing_list = wearings_by_items_id.get(item.id, [])
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
        source=source,
        personal=personal,
    )


async def list_perfumes(
    session_factory: async_sessionmaker[AsyncSession],
    q: str | None = None,
) -> list[mdl.Perfume]:
    async with session_factory() as session:
        query = select(orm.Perfume).order_by(orm.Perfume.id)
        if q and (search_term := q.strip()):
            query = query.where(
                or_(
                    orm.Perfume.brand.icontains(search_term, autoescape=True),
                    orm.Perfume.name.icontains(search_term, autoescape=True),
                )
            )

        results = await session.scalars(query)

        return [
            mdl.Perfume.model_validate(item, from_attributes=True) for item in results
        ]


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
        if matches_integrity_error(exc, "23505", "uq_brand_name_concentration_keys"):
            raise DuplicatePerfumeError("This perfume already exists.") from exc
        else:
            raise


async def delete_perfume(
    session_factory: async_sessionmaker[AsyncSession],
    perfume_id: int,
) -> None:
    try:
        async with session_factory.begin() as session:
            perfume = await session.get(orm.Perfume, perfume_id)

            if perfume is None:
                raise PerfumeNotFoundError("Perfume not found.")

            await session.delete(perfume)
            await session.flush()

    except IntegrityError as exc:
        if matches_integrity_error(exc, "23001", "collection_items_perfume_id_fkey"):
            raise PerfumeHasCollectionItemsError(
                "Cannot delete a perfume with collection items."
            ) from exc
        else:
            raise


async def update_perfume_source(
    session_factory: async_sessionmaker[AsyncSession],
    perfume_id: int,
    data: mdl.PerfumeSourceUpdate,
) -> mdl.PerfumeSource:
    async with session_factory.begin() as session:
        perfume = await session.get(orm.Perfume, perfume_id)

        if perfume is None:
            raise PerfumeNotFoundError("Perfume not found.")

        new_data = data.model_dump(mode="json", exclude_unset=True)

        for field, value in new_data.items():
            setattr(perfume, f"source_{field}", value)

        await session.flush()

        return mdl.PerfumeSource.model_validate(
            {
                "sillage": perfume.source_sillage,
                "longevity": perfume.source_longevity,
                "seasons": perfume.source_seasons,
                "times_of_day": perfume.source_times_of_day,
                "url": perfume.source_url,
            }
        )


async def update_perfume_personal(
    session_factory: async_sessionmaker[AsyncSession],
    perfume_id: int,
    data: mdl.PerfumePersonalUpdate,
) -> mdl.PerfumePersonal:
    async with session_factory.begin() as session:
        perfume = await session.get(orm.Perfume, perfume_id)

        if perfume is None:
            raise PerfumeNotFoundError("Perfume not found.")

        new_data = data.model_dump(mode="json", exclude_unset=True)

        for field, value in new_data.items():
            setattr(perfume, f"personal_{field}", value)

        await session.flush()

        return mdl.PerfumePersonal.model_validate(
            {
                "sillage": perfume.personal_sillage,
                "longevity": perfume.personal_longevity,
                "longevity_hours": perfume.personal_longevity_hours,
                "seasons": perfume.personal_seasons,
                "times_of_day": perfume.personal_times_of_day,
                "comment": perfume.personal_comment,
            }
        )
