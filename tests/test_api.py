import pytest
from fastapi.testclient import TestClient

from perfume_journal import api
from perfume_journal.in_memory_store import InMemoryStore


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    fresh_store = InMemoryStore()
    monkeypatch.setattr(api, "_store", fresh_store)

    return TestClient(api.app)


def test_create_perfume_successful(client: TestClient) -> None:

    response = client.post(
        "/perfumes", json={"brand": "Creed", "name": "Aventus", "concentration": "edp"}
    )
    data = response.json()

    assert response.status_code == 201
    assert data["brand"] == "Creed"
    assert data["name"] == "Aventus"
    assert data["concentration"] == "EDP"
    assert data["id"] == 1


def test_conflict_duplicate(client: TestClient) -> None:
    client.post(
        "/perfumes", json={"brand": "Creed", "name": "Aventus", "concentration": "edp"}
    )

    response = client.post(
        "/perfumes",
        json={"brand": "creed", "name": "AVENTUS", "concentration": "EDP"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "This perfume already exists."


def test_invalid_request_body(client: TestClient) -> None:
    response = client.post("/perfumes", json={"brand": " ", "name": "Aventus"})

    assert response.status_code == 422


def test_creates_collection_item_for_existing_perfume(client: TestClient) -> None:
    perfume_response = client.post(
        "/perfumes", json={"brand": "Creed", "name": "Aventus", "concentration": "edp"}
    )
    perfume_id = perfume_response.json()["id"]

    response = client.post(
        f"/perfumes/{perfume_id}/collection-items",
        json={"kind": "sample", "initial_volume_ml": 1.5, "acquired_on": "2026-05-09"},
    )

    item = response.json()

    assert response.status_code == 201
    assert item["id"] == 1
    assert item["perfume_id"] == perfume_id
    assert item["status"] == "active"
    assert item["kind"] == "sample"
    assert item["initial_volume_ml"] == 1.5
    assert item["acquired_on"] == "2026-05-09"


def test_missing_perfume_returns_404(client: TestClient) -> None:
    wrong_id = 1

    response = client.post(
        f"/perfumes/{wrong_id}/collection-items",
        json={"kind": "sample", "initial_volume_ml": 1.5, "acquired_on": "2026-05-09"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Perfume not found."


def test_invalid_collection_item_body_returns_422(client: TestClient) -> None:

    perfume_response = client.post(
        "/perfumes", json={"brand": "Creed", "name": "Aventus", "concentration": "edp"}
    )
    perfume_id = perfume_response.json()["id"]

    response = client.post(
        f"/perfumes/{perfume_id}/collection-items",
        json={"kind": "sample", "initial_volume_ml": -1.5, "acquired_on": "2026-05-09"},
    )

    assert response.status_code == 422
