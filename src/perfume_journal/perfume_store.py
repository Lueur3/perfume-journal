from perfume_journal.models import Perfume, PerfumeCreate


class DuplicatePerfumeError(Exception):
    pass


class PerfumeStore:
    def __init__(self) -> None:
        self._perfumes: list[Perfume] = []
        self._next_id: int = 1

    def _normalize_string(self, value: str | None) -> str | None:
        if value is None:
            return None

        return " ".join(value.split()).casefold()

    def create(self, data: PerfumeCreate) -> Perfume:
        normalized_brand = self._normalize_string(data.brand)
        normalized_name = self._normalize_string(data.name)
        normalized_concentration = self._normalize_string(data.concentration)

        for perfume in self._perfumes:
            if (
                self._normalize_string(perfume.brand) == normalized_brand
                and self._normalize_string(perfume.name) == normalized_name
                and self._normalize_string(perfume.concentration)
                == normalized_concentration
            ):
                raise DuplicatePerfumeError("This perfume already exists.")

        new_perfume = Perfume(
            brand=data.brand,
            name=data.name,
            concentration=data.concentration,
            id=self._next_id,
        )

        self._perfumes.append(new_perfume)
        self._next_id += 1

        return new_perfume
