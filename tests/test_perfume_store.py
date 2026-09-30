import pytest

from perfume_journal.models import Perfume, PerfumeCreate
from perfume_journal.perfume_store import DuplicatePerfumeError, PerfumeStore


def test_creates_first_perfume_with_expected_attributes() -> None:
    store = PerfumeStore()
    test_perfume = PerfumeCreate(brand="creed", name="aventus", concentration="EDT")

    stored_perfume = store.create(test_perfume)

    assert isinstance(stored_perfume, Perfume)
    assert stored_perfume.id == 1
    assert stored_perfume.brand == test_perfume.brand
    assert stored_perfume.name == test_perfume.name
    assert stored_perfume.concentration == test_perfume.concentration


def test_assigns_sequential_ids() -> None:
    store = PerfumeStore()
    test_perfume1 = PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")
    test_perfume2 = PerfumeCreate(
        brand="Tom Ford", name="Oud Wood", concentration="EDT"
    )

    stored_perfume1 = store.create(test_perfume1)
    stored_perfume2 = store.create(test_perfume2)

    assert stored_perfume1.id == 1
    assert stored_perfume2.id == 2


def test_duplicate_perfume_raises_error() -> None:
    store = PerfumeStore()

    perf1 = PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")
    perf2 = PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")

    store.create(perf1)

    with pytest.raises(DuplicatePerfumeError):
        store.create(perf2)


def test_normalize_values() -> None:
    store = PerfumeStore()

    perf1 = PerfumeCreate(brand="Tom Ford", name="Oud Wood", concentration="EDP")
    perf2 = PerfumeCreate(brand="tom   ford", name="OUD  WOOD", concentration="edp")

    store.create(perf1)

    with pytest.raises(DuplicatePerfumeError):
        store.create(perf2)


def test_diff_concentrations() -> None:
    store = PerfumeStore()

    perf1 = PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")
    perf2 = PerfumeCreate(brand="Creed", name="Aventus", concentration="EDP")

    stored_perf1 = store.create(perf1)
    stored_perf2 = store.create(perf2)

    assert stored_perf1.id == 1
    assert stored_perf2.id == 2


def test_failed_creation_does_not_increment_counter() -> None:
    store = PerfumeStore()

    perf1 = PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")
    duplicate_perf1 = PerfumeCreate(brand="Creed", name="Aventus", concentration="EDT")
    perf2 = PerfumeCreate(brand="Tom Ford", name="Oud Wood", concentration="EDP")

    stored_perf1 = store.create(perf1)

    with pytest.raises(DuplicatePerfumeError):
        store.create(duplicate_perf1)

    stored_perf2 = store.create(perf2)

    assert stored_perf1.id == 1
    assert stored_perf2.id == 2
