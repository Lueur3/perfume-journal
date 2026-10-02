from perfume_journal.models import (
    CollectionItem,
    CollectionItemCreate,
    Perfume,
    PerfumeCreate,
)


class DuplicatePerfumeError(Exception):
    pass


class PerfumeNotFoundError(Exception):
    pass


class InMemoryStore:
    def __init__(self) -> None:
        self._perfumes: dict[int, Perfume] = {}
        self._collection_items: dict[int, CollectionItem] = {}
        self._next_perfume_id: int = 1
        self._next_collection_item_id: int = 1

    def _normalize_string(self, value: str | None) -> str | None:
        if value is None:
            return None

        return " ".join(value.split()).casefold()

    def create_perfume(self, data: PerfumeCreate) -> Perfume:
        normalized_brand = self._normalize_string(data.brand)
        normalized_name = self._normalize_string(data.name)
        normalized_concentration = self._normalize_string(data.concentration)

        for perfume in self._perfumes.values():
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
            id=self._next_perfume_id,
        )

        self._perfumes[new_perfume.id] = new_perfume
        self._next_perfume_id += 1

        return new_perfume

    def create_collection_item(
        self, perfume_id: int, data: CollectionItemCreate
    ) -> CollectionItem:
        if self._find_perfume(perfume_id) is None:
            raise PerfumeNotFoundError("Perfume not found.")

        new_item = CollectionItem(
            id=self._next_collection_item_id,
            perfume_id=perfume_id,
            status="active",
            kind=data.kind,
            initial_volume_ml=data.initial_volume_ml,
            acquired_on=data.acquired_on,
        )

        self._collection_items[new_item.id] = new_item
        self._next_collection_item_id += 1

        return new_item

    def _find_perfume(self, perfume_id: int) -> Perfume | None:
        return self._perfumes.get(perfume_id)
