from datetime import date

import pytest

import perfume_journal.in_memory_store as ims
import perfume_journal.models as mdl


def test_creates_first_perfume_with_expected_attributes() -> None:
    store = ims.InMemoryStore()
    test_perfume = mdl.PerfumeCreate(brand="creed", name="aventus", concentration="EDT")

    stored_perfume = store.create_perfume(test_perfume)

    assert isinstance(stored_perfume, mdl.Perfume)
    assert stored_perfume.id == 1
    assert stored_perfume.brand == test_perfume.brand
    assert stored_perfume.name == test_perfume.name
    assert stored_perfume.concentration == test_perfume.concentration


def test_assigns_sequential_ids() -> None:
    store = ims.InMemoryStore()
    test_perfume1 = mdl.PerfumeCreate(
        brand="Creed", name="Aventus", concentration="EDT"
    )
    test_perfume2 = mdl.PerfumeCreate(
        brand="Tom Ford", name="Oud Wood", concentration="EDT"
    )

    stored_perfume1 = store.create_perfume(test_perfume1)
    stored_perfume2 = store.create_perfume(test_perfume2)

    assert stored_perfume1.id == 1
    assert stored_perfume2.id == 2


def test_duplicate_perfume_raises_error() -> None:
    store = ims.InMemoryStore()

    perf1 = mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")
    perf2 = mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")

    store.create_perfume(perf1)

    with pytest.raises(ims.DuplicatePerfumeError):
        store.create_perfume(perf2)


def test_normalize_values() -> None:
    store = ims.InMemoryStore()

    perf1 = mdl.PerfumeCreate(brand="Tom Ford", name="Oud Wood", concentration="EDP")
    perf2 = mdl.PerfumeCreate(brand="tom   ford", name="OUD  WOOD", concentration="edp")

    store.create_perfume(perf1)

    with pytest.raises(ims.DuplicatePerfumeError):
        store.create_perfume(perf2)


def test_diff_concentrations() -> None:
    store = ims.InMemoryStore()

    perf1 = mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")
    perf2 = mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDP")

    stored_perf1 = store.create_perfume(perf1)
    stored_perf2 = store.create_perfume(perf2)

    assert stored_perf1.id == 1
    assert stored_perf2.id == 2


def test_failed_creation_does_not_increment_counter() -> None:
    store = ims.InMemoryStore()

    perf1 = mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")
    duplicate_perf1 = mdl.PerfumeCreate(
        brand="Creed", name="Aventus", concentration="EDT"
    )
    perf2 = mdl.PerfumeCreate(brand="Tom Ford", name="Oud Wood", concentration="EDP")

    stored_perf1 = store.create_perfume(perf1)

    with pytest.raises(ims.DuplicatePerfumeError):
        store.create_perfume(duplicate_perf1)

    stored_perf2 = store.create_perfume(perf2)

    assert stored_perf1.id == 1
    assert stored_perf2.id == 2


def test_creates_collection_item_for_existing_perfume() -> None:
    store = ims.InMemoryStore()

    perf = mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")

    stored_perf = store.create_perfume(perf)

    test_item = mdl.CollectionItemCreate(
        kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
    )

    stored_item = store.create_collection_item(
        perfume_id=stored_perf.id, data=test_item
    )

    assert stored_perf.id == stored_item.perfume_id
    assert stored_item.id == 1
    assert stored_item.status == "active"
    assert stored_item.kind == "sample"
    assert stored_item.initial_volume_ml == 1.5
    assert stored_item.acquired_on == date(2026, 9, 15)


def test_missing_perfume_raises_error() -> None:
    store = ims.InMemoryStore()
    test_item = mdl.CollectionItemCreate(
        kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
    )

    with pytest.raises(ims.PerfumeNotFoundError):
        store.create_collection_item(perfume_id=1, data=test_item)


def test_allows_identical_collection_items_with_sequential_ids() -> None:
    store = ims.InMemoryStore()

    perf = mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")

    stored_perf = store.create_perfume(perf)

    test_item1 = mdl.CollectionItemCreate(
        kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
    )

    test_item2 = mdl.CollectionItemCreate(
        kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
    )

    stored_item1 = store.create_collection_item(
        perfume_id=stored_perf.id, data=test_item1
    )
    stored_item2 = store.create_collection_item(
        perfume_id=stored_perf.id, data=test_item2
    )

    assert stored_perf.id == stored_item1.perfume_id
    assert stored_perf.id == stored_item2.perfume_id
    assert stored_item1.id != stored_item2.id
    assert stored_item1.id == 1
    assert stored_item2.id == 2


def test_failed_collection_item_creation_does_not_increment_counter() -> None:
    store = ims.InMemoryStore()
    test_item = mdl.CollectionItemCreate(
        kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
    )

    with pytest.raises(ims.PerfumeNotFoundError):
        store.create_collection_item(perfume_id=1, data=test_item)

    perf = mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")

    stored_perf = store.create_perfume(perf)

    test_item2 = mdl.CollectionItemCreate(
        kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
    )

    stored_item = store.create_collection_item(
        perfume_id=stored_perf.id, data=test_item2
    )

    assert stored_item.id == 1


def test_creates_wearing_for_existing_collection_item() -> None:
    store = ims.InMemoryStore()

    perf = mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")
    stored_perf = store.create_perfume(perf)

    item = mdl.CollectionItemCreate(
        kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
    )
    stored_item = store.create_collection_item(perfume_id=stored_perf.id, data=item)

    test_wearing = mdl.WearingCreate.model_validate(
        {"worn_at": "2026-10-02T09:30:00+03:00", "rating": 5, "comment": "Test comment"}
    )
    stored_wearing = store.create_wearing(
        collection_item_id=stored_item.id, data=test_wearing
    )

    assert stored_wearing.id == 1
    assert stored_wearing.collection_item_id == stored_item.id
    assert stored_wearing.worn_at.tzinfo is not None
    assert stored_wearing.rating == 5
    assert stored_wearing.comment == "Test comment"


def test_missing_collection_item_raises_error() -> None:
    store = ims.InMemoryStore()

    test_wearing = mdl.WearingCreate.model_validate(
        {"worn_at": "2026-10-02T09:30:00+03:00"}
    )

    with pytest.raises(ims.CollectionItemNotFoundError):
        store.create_wearing(collection_item_id=1, data=test_wearing)


def test_allows_multiple_wearings_with_sequential_ids() -> None:
    store = ims.InMemoryStore()

    perf = mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")
    stored_perf = store.create_perfume(perf)
    item = mdl.CollectionItemCreate(
        kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
    )
    stored_item = store.create_collection_item(perfume_id=stored_perf.id, data=item)

    wearing1 = mdl.WearingCreate.model_validate(
        {"worn_at": "2026-10-02T09:30:00+03:00", "rating": 5, "comment": "Test comment"}
    )
    wearing2 = mdl.WearingCreate.model_validate(
        {
            "worn_at": "2026-10-02T09:30:00+03:00",
            "rating": 10,
            "comment": "Test comment",
        }
    )

    stored_wearing1 = store.create_wearing(
        collection_item_id=stored_item.id, data=wearing1
    )
    stored_wearing2 = store.create_wearing(
        collection_item_id=stored_item.id, data=wearing2
    )

    assert stored_wearing1.collection_item_id == stored_item.id
    assert stored_wearing2.collection_item_id == stored_item.id
    assert stored_wearing1.id == 1
    assert stored_wearing2.id == 2


def test_failed_wearing_creation_does_not_increment_counter() -> None:
    store = ims.InMemoryStore()

    test_wearing = mdl.WearingCreate.model_validate(
        {"worn_at": "2026-10-02T09:30:00+03:00"}
    )

    with pytest.raises(ims.CollectionItemNotFoundError):
        store.create_wearing(collection_item_id=1, data=test_wearing)

    perf = mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")
    stored_perf = store.create_perfume(perf)
    item = mdl.CollectionItemCreate(
        kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
    )
    stored_item = store.create_collection_item(perfume_id=stored_perf.id, data=item)

    wearing = mdl.WearingCreate.model_validate(
        {"worn_at": "2026-10-02T09:30:00+03:00", "rating": 5, "comment": "Test comment"}
    )

    stored_wearing = store.create_wearing(
        collection_item_id=stored_item.id, data=wearing
    )

    assert stored_wearing.id == 1
