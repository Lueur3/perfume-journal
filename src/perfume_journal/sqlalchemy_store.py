from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import perfume_journal.models as mdl
import perfume_journal.orm_models as orm
from perfume_journal.errors import DuplicatePerfumeError, PerfumeNotFoundError
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
