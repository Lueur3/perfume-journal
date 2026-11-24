from datetime import date
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    Field,
    HttpUrl,
    PositiveFloat,
    StringConstraints,
    ValidationInfo,
    field_validator,
)

_KNOWN_CONCENTRATION_ABBREVIATIONS = {"edt", "edp", "edc"}

CleanString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

CollectionItemKind = Literal["sample", "bottle"]
CollectionItemStatus = Literal["active", "archived"]

WearingRating = Annotated[int, Field(ge=1, le=10)]

PerfumeSillage = Literal["none", "close_to_skin", "arms_length", "fills_room"]
PerfumeLongevity = Literal["very_short", "short", "moderate", "long", "very_long"]
PerfumeSeason = Literal["winter", "spring", "summer", "autumn"]
PerfumeTimeOfDay = Literal["day", "evening"]
PersonalLongevityHours = Annotated[float, Field(gt=0, le=24)]


class PerfumeCreate(BaseModel):
    brand: CleanString
    name: CleanString
    concentration: CleanString | None = None

    @field_validator("concentration", mode="after")
    @classmethod
    def canonicalize_concentration(cls, concentration: str | None) -> str | None:
        if concentration is None:
            return None
        if concentration.casefold() in _KNOWN_CONCENTRATION_ABBREVIATIONS:
            return concentration.upper()

        return concentration


class Perfume(PerfumeCreate):
    id: int


class CollectionItemCreate(BaseModel):
    kind: CollectionItemKind
    initial_volume_ml: PositiveFloat | None = None
    acquired_on: date | None = None


class CollectionItem(CollectionItemCreate):
    id: int
    perfume_id: int
    status: CollectionItemStatus


class WearingCreate(BaseModel):
    worn_at: AwareDatetime
    rating: WearingRating | None = None
    comment: CleanString | None = None


class Wearing(WearingCreate):
    id: int
    collection_item_id: int


class CollectionItemDetails(CollectionItem):
    wearings: list[Wearing]


class CollectionItemUpdate(BaseModel):
    kind: CollectionItemKind | None = None
    initial_volume_ml: PositiveFloat | None = None
    acquired_on: date | None = None
    status: CollectionItemStatus | None = None

    @field_validator("kind", "status", mode="after")
    @classmethod
    def reject_null(
        cls,
        value: CollectionItemKind | CollectionItemStatus | None,
        info: ValidationInfo,
    ) -> CollectionItemKind | CollectionItemStatus:
        if value is None:
            raise ValueError(f"{info.field_name} can't be None.")

        return value


class PerfumeSource(BaseModel):
    sillage: PerfumeSillage | None
    longevity: PerfumeLongevity | None
    seasons: list[PerfumeSeason] | None
    times_of_day: list[PerfumeTimeOfDay] | None
    url: str | None


class PerfumePersonal(BaseModel):
    sillage: PerfumeSillage | None
    longevity: PerfumeLongevity | None
    longevity_hours: PersonalLongevityHours | None
    seasons: list[PerfumeSeason] | None
    times_of_day: list[PerfumeTimeOfDay] | None
    comment: str | None


class PerfumeSourceUpdate(BaseModel):
    sillage: PerfumeSillage | None = None
    longevity: PerfumeLongevity | None = None
    seasons: list[PerfumeSeason] | None = None
    times_of_day: list[PerfumeTimeOfDay] | None = None
    url: HttpUrl | None = None


class PerfumePersonalUpdate(BaseModel):
    sillage: PerfumeSillage | None = None
    longevity: PerfumeLongevity | None = None
    longevity_hours: PersonalLongevityHours | None = None
    seasons: list[PerfumeSeason] | None = None
    times_of_day: list[PerfumeTimeOfDay] | None = None
    comment: str | None = None


class PerfumeDetails(Perfume):
    collection_items: list[CollectionItemDetails]
    average_rating: float | None
    source: PerfumeSource
    personal: PerfumePersonal
