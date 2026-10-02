from datetime import date

import pytest
from pydantic import ValidationError

from perfume_journal.models import CollectionItem, CollectionItemCreate, PerfumeCreate


def test_canonicalizes_known_abbreviation() -> None:
    perf1 = PerfumeCreate(brand="Creed", name="Aventus", concentration="edp")
    perf2 = PerfumeCreate(brand="Creed", name="Aventus", concentration="eDt")
    perf3 = PerfumeCreate(
        brand="Creed", name="Aventus", concentration="Extrait de Parfum"
    )
    perf4 = PerfumeCreate(
        brand="Creed",
        name="Aventus",
    )

    assert perf1.concentration == "EDP"
    assert perf2.concentration == "EDT"
    assert perf3.concentration == "Extrait de Parfum"
    assert perf4.concentration is None
    assert perf1.brand == "Creed"
    assert perf1.name == "Aventus"


def test_correct_collection_item_create() -> None:
    test_collection_item = CollectionItemCreate(
        kind="bottle", initial_volume_ml=2.0, acquired_on=date(2026, 5, 9)
    )

    assert test_collection_item.kind == "bottle"
    assert test_collection_item.initial_volume_ml == 2.0
    assert test_collection_item.acquired_on == date(2026, 5, 9)


def test_collection_item_create_defaults_optional_fields_to_none() -> None:
    test_collection_item = CollectionItemCreate(kind="bottle")

    assert test_collection_item.kind == "bottle"
    assert test_collection_item.initial_volume_ml is None
    assert test_collection_item.acquired_on is None


def test_rejects_invalid_kind() -> None:
    with pytest.raises(ValidationError):
        CollectionItemCreate.model_validate({"kind": "decant"})


def test_rejects_zero_or_negative_volume() -> None:
    with pytest.raises(ValidationError):
        CollectionItemCreate(kind="bottle", initial_volume_ml=0)

    with pytest.raises(ValidationError):
        CollectionItemCreate(kind="bottle", initial_volume_ml=-2)


def test_correct_collection_item() -> None:
    test_collection_item = CollectionItem(
        kind="sample",
        initial_volume_ml=2.0,
        acquired_on=date(2026, 5, 9),
        id=1,
        perfume_id=5,
        status="active",
    )

    assert test_collection_item.kind == "sample"
    assert test_collection_item.initial_volume_ml == 2.0
    assert test_collection_item.acquired_on == date(2026, 5, 9)
    assert test_collection_item.id == 1
    assert test_collection_item.perfume_id == 5
    assert test_collection_item.status == "active"
