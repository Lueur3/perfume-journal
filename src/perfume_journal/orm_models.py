from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Double,
    ForeignKey,
    Identity,
    SmallInteger,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Perfume(Base):
    __tablename__ = "perfumes"

    __table_args__ = (
        UniqueConstraint(
            "brand_key",
            "name_key",
            "concentration_key",
            name="uq_brand_name_concentration_keys",
            postgresql_nulls_not_distinct=True,
        ),
        CheckConstraint(
            "source_sillage IN ('none', 'close_to_skin', 'arms_length', 'fills_room')",
            name="ck_source_sillage",
        ),
        CheckConstraint(
            "personal_sillage IN ('none', 'close_to_skin', 'arms_length', 'fills_room')",
            name="ck_personal_sillage",
        ),
        CheckConstraint(
            "source_longevity IN ('very_short', 'short', 'moderate', 'long', 'very_long')",
            name="ck_source_longevity",
        ),
        CheckConstraint(
            "personal_longevity IN ('very_short', 'short', 'moderate', 'long', 'very_long')",
            name="ck_personal_longevity",
        ),
        CheckConstraint(
            "personal_longevity_hours > 0 AND personal_longevity_hours <= 24",
            name="ck_personal_longevity_hours",
        ),
        CheckConstraint(
            "source_seasons <@ ARRAY['winter', 'spring', 'summer', 'autumn']::text[]",
            name="ck_source_seasons",
        ),
        CheckConstraint(
            "personal_seasons <@ ARRAY['winter', 'spring', 'summer', 'autumn']::text[]",
            name="ck_personal_seasons",
        ),
        CheckConstraint(
            "source_times_of_day <@ ARRAY['day', 'evening']::text[]",
            name="ck_source_times_of_day",
        ),
        CheckConstraint(
            "personal_times_of_day <@ ARRAY['day', 'evening']::text[]",
            name="ck_personal_times_of_day",
        ),
    )

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    brand: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    concentration: Mapped[str | None] = mapped_column(Text)

    brand_key: Mapped[str] = mapped_column(Text)
    name_key: Mapped[str] = mapped_column(Text)
    concentration_key: Mapped[str | None] = mapped_column(Text)

    source_sillage: Mapped[str | None] = mapped_column(Text)
    personal_sillage: Mapped[str | None] = mapped_column(Text)

    source_longevity: Mapped[str | None] = mapped_column(Text)
    personal_longevity: Mapped[str | None] = mapped_column(Text)

    source_url: Mapped[str | None] = mapped_column(Text)
    personal_comment: Mapped[str | None] = mapped_column(Text)
    personal_longevity_hours: Mapped[float | None] = mapped_column(Double)

    source_seasons: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    personal_seasons: Mapped[list[str] | None] = mapped_column(ARRAY(Text))

    source_times_of_day: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    personal_times_of_day: Mapped[list[str] | None] = mapped_column(ARRAY(Text))


class CollectionItem(Base):
    __tablename__ = "collection_items"

    __table_args__ = (
        CheckConstraint(
            "kind IN ('sample', 'bottle')",
            name="ck_collection_items_kind",
        ),
        CheckConstraint(
            "status IN ('active', 'archived')",
            name="ck_collection_items_status",
        ),
        CheckConstraint(
            "initial_volume_ml > 0", name="ck_collection_items_initial_volume_ml"
        ),
    )

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    perfume_id: Mapped[int] = mapped_column(
        ForeignKey("perfumes.id", ondelete="RESTRICT")
    )
    kind: Mapped[str] = mapped_column(Text)
    initial_volume_ml: Mapped[float | None] = mapped_column(Double)
    acquired_on: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(Text, server_default="active")


class Wearing(Base):
    __tablename__ = "wearings"

    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 10", name="ck_wearings_rating"),
    )

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    collection_item_id: Mapped[int] = mapped_column(
        ForeignKey("collection_items.id", ondelete="RESTRICT")
    )
    worn_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    rating: Mapped[int | None] = mapped_column(SmallInteger)
    comment: Mapped[str | None] = mapped_column(Text)
