from datetime import date

import pytest
from pydantic import ValidationError

import perfume_journal.models as mdl


def test_canonicalizes_known_abbreviation() -> None:
    perf1 = mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="edp")
    perf2 = mdl.PerfumeCreate(brand="Creed", name="Aventus", concentration="eDt")
    perf3 = mdl.PerfumeCreate(
        brand="Creed", name="Aventus", concentration="Extrait de Parfum"
    )
    perf4 = mdl.PerfumeCreate(
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
    test_collection_item = mdl.CollectionItemCreate(
        kind="bottle", initial_volume_ml=2.0, acquired_on=date(2026, 5, 9)
    )

    assert test_collection_item.kind == "bottle"
    assert test_collection_item.initial_volume_ml == 2.0
    assert test_collection_item.acquired_on == date(2026, 5, 9)


def test_collection_item_create_defaults_optional_fields_to_none() -> None:
    test_collection_item = mdl.CollectionItemCreate(kind="bottle")

    assert test_collection_item.kind == "bottle"
    assert test_collection_item.initial_volume_ml is None
    assert test_collection_item.acquired_on is None


def test_rejects_invalid_kind() -> None:
    with pytest.raises(ValidationError):
        mdl.CollectionItemCreate.model_validate({"kind": "decant"})


def test_rejects_zero_or_negative_volume() -> None:
    with pytest.raises(ValidationError):
        mdl.CollectionItemCreate(kind="bottle", initial_volume_ml=0)

    with pytest.raises(ValidationError):
        mdl.CollectionItemCreate(kind="bottle", initial_volume_ml=-2)


def test_correct_collection_item() -> None:
    test_collection_item = mdl.CollectionItem(
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


def test_correct_wearing_create_fields() -> None:
    test_wearing_create_item = mdl.WearingCreate.model_validate(
        {"worn_at": "2026-10-02T09:30:00+03:00", "rating": 5, "comment": "Test comment"}
    )

    assert test_wearing_create_item.worn_at.tzinfo is not None
    assert test_wearing_create_item.rating == 5
    assert test_wearing_create_item.comment == "Test comment"


def test_wearing_create_defaults_optional_fields_to_none() -> None:
    test_wearing_create_item = mdl.WearingCreate.model_validate(
        {"worn_at": "2026-10-02T09:30:00+03:00"}
    )

    assert test_wearing_create_item.worn_at.tzinfo is not None
    assert test_wearing_create_item.rating is None
    assert test_wearing_create_item.comment is None


def test_wearing_create_invalid_rates() -> None:
    with pytest.raises(ValidationError):
        mdl.WearingCreate.model_validate(
            {"worn_at": "2026-10-02T09:30:00+03:00", "rating": 0}
        )

    with pytest.raises(ValidationError):
        mdl.WearingCreate.model_validate(
            {"worn_at": "2026-10-02T09:30:00+03:00", "rating": 11}
        )


def test_wearing_create_invalid_worn_at() -> None:
    with pytest.raises(ValidationError):
        mdl.WearingCreate.model_validate({"worn_at": "2026-10-02T09:30:00"})


def test_correct_wearing() -> None:
    wearing = mdl.Wearing.model_validate(
        {
            "id": 1,
            "collection_item_id": 5,
            "worn_at": "2026-10-02T09:30:00+03:00",
            "rating": 5,
            "comment": "Test comment",
        }
    )

    assert wearing.id == 1
    assert wearing.collection_item_id == 5
    assert wearing.worn_at.tzinfo is not None
    assert wearing.rating == 5
    assert wearing.comment == "Test comment"


def test_nested_details_perfume_model() -> None:
    test_data = {
        "id": 1,
        "brand": "Creed",
        "name": "Aventus",
        "concentration": "EDP",
        "collection_items": [
            {
                "id": 1,
                "perfume_id": 1,
                "kind": "sample",
                "initial_volume_ml": 1.5,
                "acquired_on": "2026-05-09",
                "status": "active",
                "wearings": [
                    {
                        "id": 1,
                        "collection_item_id": 1,
                        "worn_at": "2026-10-02T09:30:00+03:00",
                        "rating": 5,
                        "comment": "Test comment",
                    }
                ],
            }
        ],
        "average_rating": 5.0,
    }

    perfume = mdl.PerfumeDetails.model_validate(test_data)

    assert perfume.id == 1
    assert perfume.brand == "Creed"
    assert perfume.name == "Aventus"
    assert perfume.concentration == "EDP"
    assert perfume.average_rating == 5.0
    assert perfume.collection_items[0].id == 1
    assert perfume.collection_items[0].perfume_id == 1
    assert perfume.collection_items[0].kind == "sample"
    assert perfume.collection_items[0].initial_volume_ml == 1.5
    assert perfume.collection_items[0].acquired_on == date(2026, 5, 9)
    assert perfume.collection_items[0].status == "active"
    assert perfume.collection_items[0].wearings[0].id == 1
    assert perfume.collection_items[0].wearings[0].collection_item_id == 1
    assert perfume.collection_items[0].wearings[0].worn_at.tzinfo is not None
    assert perfume.collection_items[0].wearings[0].rating == 5
    assert perfume.collection_items[0].wearings[0].comment == "Test comment"
