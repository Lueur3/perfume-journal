import perfume_journal.models as mdl
from perfume_journal.errors import DuplicatePerfumeError, PerfumeNotFoundError
from perfume_journal.normalization import create_key


class CollectionItemNotFoundError(Exception):
    pass


class InMemoryStore:
    def __init__(self) -> None:
        self._perfumes: dict[int, mdl.Perfume] = {}
        self._collection_items: dict[int, mdl.CollectionItem] = {}
        self._wearings: dict[int, mdl.Wearing] = {}

        self._next_perfume_id: int = 1
        self._next_collection_item_id: int = 1
        self._next_wearing_id: int = 1

    def create_perfume(self, data: mdl.PerfumeCreate) -> mdl.Perfume:
        normalized_brand = create_key(data.brand)
        normalized_name = create_key(data.name)
        normalized_concentration = create_key(data.concentration)

        for perfume in self._perfumes.values():
            if (
                create_key(perfume.brand) == normalized_brand
                and create_key(perfume.name) == normalized_name
                and create_key(perfume.concentration) == normalized_concentration
            ):
                raise DuplicatePerfumeError("This perfume already exists.")

        new_perfume = mdl.Perfume(
            brand=data.brand,
            name=data.name,
            concentration=data.concentration,
            id=self._next_perfume_id,
        )

        self._perfumes[new_perfume.id] = new_perfume
        self._next_perfume_id += 1

        return new_perfume

    def create_collection_item(
        self, perfume_id: int, data: mdl.CollectionItemCreate
    ) -> mdl.CollectionItem:
        if self._find_perfume(perfume_id) is None:
            raise PerfumeNotFoundError("Perfume not found.")

        new_item = mdl.CollectionItem(
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

    def create_wearing(
        self, collection_item_id: int, data: mdl.WearingCreate
    ) -> mdl.Wearing:
        if self._find_collection_item(collection_item_id) is None:
            raise CollectionItemNotFoundError("Collection item not found.")

        new_wearing = mdl.Wearing(
            id=self._next_wearing_id,
            collection_item_id=collection_item_id,
            worn_at=data.worn_at,
            rating=data.rating,
            comment=data.comment,
        )

        self._wearings[new_wearing.id] = new_wearing
        self._next_wearing_id += 1

        return new_wearing

    def _find_perfume(self, perfume_id: int) -> mdl.Perfume | None:
        return self._perfumes.get(perfume_id)

    def _find_collection_item(
        self, collection_item_id: int
    ) -> mdl.CollectionItem | None:
        return self._collection_items.get(collection_item_id)

    def get_perfume_details(self, perfume_id: int) -> mdl.PerfumeDetails:
        perfume = self._find_perfume(perfume_id)
        if perfume is None:
            raise PerfumeNotFoundError("Perfume not found.")

        collection_items_details_list = []

        for item in self._collection_items.values():
            if item.perfume_id != perfume_id:
                continue

            wearing_list = []

            for wearing in self._wearings.values():
                if wearing.collection_item_id == item.id:
                    wearing_list.append(wearing)

            collection_item_details = mdl.CollectionItemDetails(
                **item.model_dump(), wearings=wearing_list
            )
            collection_items_details_list.append(collection_item_details)

        ratings = [
            wearing.rating
            for item in collection_items_details_list
            for wearing in item.wearings
            if wearing.rating is not None
        ]

        average_rating = sum(ratings) / len(ratings) if ratings else None

        return mdl.PerfumeDetails(
            **perfume.model_dump(),
            collection_items=collection_items_details_list,
            average_rating=average_rating,
        )
