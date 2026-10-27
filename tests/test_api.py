from collections.abc import AsyncGenerator
from datetime import datetime

import pytest
from httpx2 import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from perfume_journal import api


@pytest.fixture
async def async_client(
    monkeypatch: pytest.MonkeyPatch, session_factory: async_sessionmaker[AsyncSession]
) -> AsyncGenerator[AsyncClient]:
    def override_session_factory() -> async_sessionmaker[AsyncSession]:
        return session_factory

    monkeypatch.setitem(
        api.app.dependency_overrides,
        api.get_session_factory,
        override_session_factory,
    )

    async with AsyncClient(
        transport=ASGITransport(app=api.app),
        base_url="http://test",
    ) as async_client:
        yield async_client


@pytest.mark.anyio
async def test_create_perfume_successful(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/perfumes", json={"brand": "Creed", "name": "Aventus", "concentration": "edp"}
    )
    data = response.json()

    assert response.status_code == 201
    assert data["brand"] == "Creed"
    assert data["name"] == "Aventus"
    assert data["concentration"] == "EDP"
    assert data["id"] > 0


@pytest.mark.anyio
async def test_conflict_duplicate(async_client: AsyncClient) -> None:
    await async_client.post(
        "/perfumes", json={"brand": "Creed", "name": "Aventus", "concentration": "edp"}
    )

    response = await async_client.post(
        "/perfumes",
        json={"brand": "creed", "name": "AVENTUS", "concentration": "EDP"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "This perfume already exists."


@pytest.mark.anyio
async def test_invalid_request_body(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/perfumes", json={"brand": " ", "name": "Aventus"}
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_creates_collection_item_for_existing_perfume(
    async_client: AsyncClient,
) -> None:
    perfume_response = await async_client.post(
        "/perfumes", json={"brand": "Creed", "name": "Aventus", "concentration": "edp"}
    )
    perfume_id = perfume_response.json()["id"]

    response = await async_client.post(
        f"/perfumes/{perfume_id}/collection-items",
        json={"kind": "sample", "initial_volume_ml": 1.5, "acquired_on": "2026-05-09"},
    )

    item = response.json()

    assert response.status_code == 201
    assert item["id"] > 0
    assert item["perfume_id"] == perfume_id
    assert item["status"] == "active"
    assert item["kind"] == "sample"
    assert item["initial_volume_ml"] == 1.5
    assert item["acquired_on"] == "2026-05-09"


@pytest.mark.anyio
async def test_missing_perfume_returns_404(async_client: AsyncClient) -> None:
    wrong_id = 1

    response = await async_client.post(
        f"/perfumes/{wrong_id}/collection-items",
        json={"kind": "sample", "initial_volume_ml": 1.5, "acquired_on": "2026-05-09"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Perfume not found."


@pytest.mark.anyio
async def test_invalid_collection_item_body_returns_422(
    async_client: AsyncClient,
) -> None:

    perfume_response = await async_client.post(
        "/perfumes", json={"brand": "Creed", "name": "Aventus", "concentration": "edp"}
    )
    perfume_id = perfume_response.json()["id"]

    response = await async_client.post(
        f"/perfumes/{perfume_id}/collection-items",
        json={"kind": "sample", "initial_volume_ml": -1.5, "acquired_on": "2026-05-09"},
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_create_wearing(async_client: AsyncClient) -> None:
    perfume_response = await async_client.post(
        "/perfumes", json={"brand": "Creed", "name": "Aventus", "concentration": "edp"}
    )
    perfume_id = perfume_response.json()["id"]

    item_response = await async_client.post(
        f"/perfumes/{perfume_id}/collection-items",
        json={"kind": "sample", "initial_volume_ml": 1.5, "acquired_on": "2026-05-09"},
    )
    collection_item_id = item_response.json()["id"]

    response = await async_client.post(
        f"/collection-items/{collection_item_id}/wearings",
        json={
            "worn_at": "2026-10-02T09:30:00+03:00",
            "rating": 5,
            "comment": "Test comment",
        },
    )

    wearing = response.json()

    assert response.status_code == 201
    assert wearing["id"] > 0
    assert wearing["collection_item_id"] == collection_item_id
    assert datetime.fromisoformat(wearing["worn_at"]) == datetime.fromisoformat(
        "2026-10-02T09:30:00+03:00"
    )
    assert wearing["rating"] == 5
    assert wearing["comment"] == "Test comment"


@pytest.mark.anyio
async def test_missing_collection_item_returns_404(async_client: AsyncClient) -> None:
    wrong_id = 1

    response = await async_client.post(
        f"/collection-items/{wrong_id}/wearings",
        json={
            "worn_at": "2026-10-02T09:30:00+03:00",
            "rating": 5,
            "comment": "Test comment",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Collection item not found."


@pytest.mark.anyio
async def test_invalid_wearing_body_returns_422(async_client: AsyncClient) -> None:
    perfume_response = await async_client.post(
        "/perfumes", json={"brand": "Creed", "name": "Aventus", "concentration": "edp"}
    )
    perfume_id = perfume_response.json()["id"]

    item_response = await async_client.post(
        f"/perfumes/{perfume_id}/collection-items",
        json={"kind": "sample", "initial_volume_ml": 1.5, "acquired_on": "2026-05-09"},
    )
    collection_item_id = item_response.json()["id"]

    response = await async_client.post(
        f"/collection-items/{collection_item_id}/wearings",
        json={
            "worn_at": "2026-10-02T09:30:00+03:00",
            "rating": -5,
            "comment": "Test comment",
        },
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_correct_get_perfume(async_client: AsyncClient) -> None:
    perfume_response = await async_client.post(
        "/perfumes", json={"brand": "Creed", "name": "Aventus", "concentration": "edp"}
    )
    perfume_id = perfume_response.json()["id"]

    item_response = await async_client.post(
        f"/perfumes/{perfume_id}/collection-items",
        json={"kind": "sample", "initial_volume_ml": 1.5, "acquired_on": "2026-05-09"},
    )
    collection_item_id = item_response.json()["id"]

    wearing_response = await async_client.post(
        f"/collection-items/{collection_item_id}/wearings",
        json={
            "worn_at": "2026-10-02T09:30:00+03:00",
            "rating": 5,
            "comment": "Test comment",
        },
    )
    wearing_id = wearing_response.json()["id"]

    response = await async_client.get(f"/perfumes/{perfume_id}")
    details = response.json()

    assert response.status_code == 200
    assert details["id"] > 0
    assert details["id"] == perfume_id
    assert details["brand"] == "Creed"
    assert details["name"] == "Aventus"
    assert details["concentration"] == "EDP"
    assert details["average_rating"] == 5.0
    assert len(details["collection_items"]) == 1
    assert len(details["collection_items"][0]["wearings"]) == 1
    assert details["collection_items"][0]["id"] > 0
    assert details["collection_items"][0]["id"] == collection_item_id
    assert details["collection_items"][0]["perfume_id"] > 0
    assert details["collection_items"][0]["perfume_id"] == perfume_id
    assert details["collection_items"][0]["kind"] == "sample"
    assert details["collection_items"][0]["initial_volume_ml"] == 1.5
    assert details["collection_items"][0]["acquired_on"] == "2026-05-09"
    assert details["collection_items"][0]["status"] == "active"
    assert details["collection_items"][0]["wearings"][0]["id"] > 0
    assert details["collection_items"][0]["wearings"][0]["id"] == wearing_id
    assert details["collection_items"][0]["wearings"][0]["collection_item_id"] > 0
    assert (
        details["collection_items"][0]["wearings"][0]["collection_item_id"]
        == collection_item_id
    )
    assert datetime.fromisoformat(
        details["collection_items"][0]["wearings"][0]["worn_at"]
    ) == datetime.fromisoformat("2026-10-02T09:30:00+03:00")
    assert details["collection_items"][0]["wearings"][0]["rating"] == 5
    assert details["collection_items"][0]["wearings"][0]["comment"] == "Test comment"


@pytest.mark.anyio
async def test_not_found_perfume(async_client: AsyncClient) -> None:
    response = await async_client.get("/perfumes/1")
    detail = response.json()["detail"]

    assert response.status_code == 404
    assert detail == "Perfume not found."


@pytest.mark.anyio
async def test_correct_perfume_update(async_client: AsyncClient) -> None:
    perfume_response = await async_client.post(
        "/perfumes", json={"brand": "Creed", "name": "Aventus", "concentration": "edp"}
    )
    perfume_id = perfume_response.json()["id"]

    response = await async_client.put(
        f"/perfumes/{perfume_id}",
        json={"brand": "Tom Ford", "name": "Oud Wood", "concentration": "edt"},
    )
    item = response.json()

    assert response.status_code == 200
    assert item["id"] == perfume_id
    assert item["brand"] == "Tom Ford"
    assert item["name"] == "Oud Wood"
    assert item["concentration"] == "EDT"

    response_get = await async_client.get(f"/perfumes/{perfume_id}")
    item_get = response_get.json()

    assert response_get.status_code == 200
    assert item_get["id"] == perfume_id
    assert item_get["brand"] == "Tom Ford"
    assert item_get["name"] == "Oud Wood"
    assert item_get["concentration"] == "EDT"


@pytest.mark.anyio
async def test_not_exsists_perfume_update(async_client: AsyncClient) -> None:
    response = await async_client.put(
        "/perfumes/1",
        json={"brand": "Tom Ford", "name": "Oud Wood", "concentration": "edt"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Perfume not found."


@pytest.mark.anyio
async def test_duplicate_perfume_update(async_client: AsyncClient) -> None:
    await async_client.post(
        "/perfumes", json={"brand": "Creed", "name": "Aventus", "concentration": "edp"}
    )

    perfume_response = await async_client.post(
        "/perfumes",
        json={"brand": "Tom Ford", "name": "Oud Wood", "concentration": "edt"},
    )
    perfume_id = perfume_response.json()["id"]

    response = await async_client.put(
        f"/perfumes/{perfume_id}",
        json={"brand": "Creed", "name": "Aventus", "concentration": "edp"},
    )

    detail = response.json()["detail"]
    assert response.status_code == 409
    assert detail == "This perfume already exists."


@pytest.mark.anyio
async def test_wrong_data_perfume_update(async_client: AsyncClient) -> None:
    perfume_response = await async_client.post(
        "/perfumes",
        json={"brand": "Tom Ford", "name": "Oud Wood", "concentration": "edt"},
    )
    perfume_id = perfume_response.json()["id"]

    response = await async_client.put(
        f"/perfumes/{perfume_id}",
        json={"brand": "  ", "name": "Aventus", "concentration": "edp"},
    )

    assert response.status_code == 422

    response_get = await async_client.get(f"/perfumes/{perfume_id}")
    item_get = response_get.json()

    assert response_get.status_code == 200
    assert item_get["id"] == perfume_id
    assert item_get["brand"] == "Tom Ford"
    assert item_get["name"] == "Oud Wood"
    assert item_get["concentration"] == "EDT"
