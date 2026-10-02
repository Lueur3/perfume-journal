from datetime import date

import pytest

from perfume_journal.in_memory_store import (
    DuplicatePerfumeError,
    InMemoryStore,
    PerfumeNotFoundError,
)
from perfume_journal.models import CollectionItemCreate, Perfume, PerfumeCreate


def test_creates_first_perfume_with_expected_attributes() -> None:
    store = InMemoryStore()
    test_perfume = PerfumeCreate(brand="creed", name="aventus", concentration="EDT")

    stored_perfume = store.create_perfume(test_perfume)

    assert isinstance(stored_perfume, Perfume)
    assert stored_perfume.id == 1
    assert stored_perfume.brand == test_perfume.brand
    assert stored_perfume.name == test_perfume.name
    assert stored_perfume.concentration == test_perfume.concentration


def test_assigns_sequential_ids() -> None:
    store = InMemoryStore()
    test_perfume1 = PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")
    test_perfume2 = PerfumeCreate(
        brand="Tom Ford", name="Oud Wood", concentration="EDT"
    )

    stored_perfume1 = store.create_perfume(test_perfume1)
    stored_perfume2 = store.create_perfume(test_perfume2)

    assert stored_perfume1.id == 1
    assert stored_perfume2.id == 2


def test_duplicate_perfume_raises_error() -> None:
    store = InMemoryStore()

    perf1 = PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")
    perf2 = PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")

    store.create_perfume(perf1)

    with pytest.raises(DuplicatePerfumeError):
        store.create_perfume(perf2)


def test_normalize_values() -> None:
    store = InMemoryStore()

    perf1 = PerfumeCreate(brand="Tom Ford", name="Oud Wood", concentration="EDP")
    perf2 = PerfumeCreate(brand="tom   ford", name="OUD  WOOD", concentration="edp")

    store.create_perfume(perf1)

    with pytest.raises(DuplicatePerfumeError):
        store.create_perfume(perf2)


def test_diff_concentrations() -> None:
    store = InMemoryStore()

    perf1 = PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")
    perf2 = PerfumeCreate(brand="Creed", name="Aventus", concentration="EDP")

    stored_perf1 = store.create_perfume(perf1)
    stored_perf2 = store.create_perfume(perf2)

    assert stored_perf1.id == 1
    assert stored_perf2.id == 2


def test_failed_creation_does_not_increment_counter() -> None:
    store = InMemoryStore()

    perf1 = PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")
    duplicate_perf1 = PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")
    perf2 = PerfumeCreate(brand="Tom Ford", name="Oud Wood", concentration="EDP")

    stored_perf1 = store.create_perfume(perf1)

    with pytest.raises(DuplicatePerfumeError):
        store.create_perfume(duplicate_perf1)

    stored_perf2 = store.create_perfume(perf2)

    assert stored_perf1.id == 1
    assert stored_perf2.id == 2


def test_creates_collection_item_for_existing_perfume() -> None:
    store = InMemoryStore()

    perf = PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")

    stored_perf = store.create_perfume(perf)

    test_item = CollectionItemCreate(
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
    store = InMemoryStore()
    test_item = CollectionItemCreate(
        kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
    )

    with pytest.raises(PerfumeNotFoundError):
        store.create_collection_item(perfume_id=1, data=test_item)


def test_allows_identical_collection_items_with_sequential_ids() -> None:
    store = InMemoryStore()

    perf = PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")

    stored_perf = store.create_perfume(perf)

    test_item1 = CollectionItemCreate(
        kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
    )

    test_item2 = CollectionItemCreate(
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
    store = InMemoryStore()
    test_item = CollectionItemCreate(
        kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
    )

    with pytest.raises(PerfumeNotFoundError):
        store.create_collection_item(perfume_id=1, data=test_item)

    perf = PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")

    stored_perf = store.create_perfume(perf)

    test_item2 = CollectionItemCreate(
        kind="sample", initial_volume_ml=1.5, acquired_on=date(2026, 9, 15)
    )

    stored_item = store.create_collection_item(
        perfume_id=stored_perf.id, data=test_item2
    )

    assert stored_item.id == 1
