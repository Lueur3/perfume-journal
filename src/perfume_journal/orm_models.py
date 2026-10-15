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
    )

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    brand: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    concentration: Mapped[str | None] = mapped_column(Text)
    brand_key: Mapped[str] = mapped_column(Text)
    name_key: Mapped[str] = mapped_column(Text)
    concentration_key: Mapped[str | None] = mapped_column(Text)


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
