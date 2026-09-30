import pytest
from fastapi.testclient import TestClient

from perfume_journal import api
from perfume_journal.perfume_store import PerfumeStore


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    fresh_store = PerfumeStore()
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
