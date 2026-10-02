from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, PositiveFloat, StringConstraints, field_validator

_KNOWN_CONCENTRATION_ABBREVIATIONS = {"edt", "edp", "edc"}

CleanString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

CollectionItemKind = Literal["sample", "bottle"]
CollectionItemStatus = Literal["active", "archived"]


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
