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


@pytest.mark.anyio
async def test_perfume_update(async_client: AsyncClient) -> None:
    perfume_response = await async_client.post(
        "/perfumes",
        json={"brand": "Tom Ford", "name": "Oud Wood", "concentration": "edt"},
    )
    perfume_id = perfume_response.json()["id"]

    item_response = await async_client.post(
        f"/perfumes/{perfume_id}/collection-items",
        json={"kind": "sample", "initial_volume_ml": 1.5, "acquired_on": "2026-05-09"},
    )
    collection_item_id = item_response.json()["id"]

    await async_client.post(
        f"/collection-items/{collection_item_id}/wearings",
        json={
            "worn_at": "2026-10-02T09:30:00+03:00",
            "rating": 5,
            "comment": "Test comment",
        },
    )

    await async_client.patch(
        f"/collection-items/{collection_item_id}", json={"status": "archived"}
    )

    details_before_response = await async_client.get(f"/perfumes/{perfume_id}")
    assert details_before_response.status_code == 200
    details_before = details_before_response.json()

    assert len(details_before["collection_items"]) == 1
    assert details_before["collection_items"][0]["status"] == "archived"
    assert details_before["average_rating"] == 5

    updated_perfume_response = await async_client.put(
        f"/perfumes/{perfume_id}",
        json={"brand": "Creed", "name": "Aventus", "concentration": "edp"},
    )
    assert updated_perfume_response.status_code == 200
    updated_perfume = updated_perfume_response.json()

    details_after_response = await async_client.get(f"/perfumes/{perfume_id}")
    assert details_after_response.status_code == 200
    details_after = details_after_response.json()

    assert updated_perfume["id"] == perfume_id
    assert updated_perfume["brand"] == "Creed"
    assert updated_perfume["name"] == "Aventus"
    assert updated_perfume["concentration"] == "EDP"

    assert details_after["collection_items"] == details_before["collection_items"]
    assert details_after["average_rating"] == details_before["average_rating"]


@pytest.mark.anyio
async def test_empty_list_perfumes(async_client: AsyncClient) -> None:
    results = await async_client.get("/perfumes")

    assert results.status_code == 200
    assert results.json() == []


@pytest.mark.anyio
async def test_correct_list_perfumes(async_client: AsyncClient) -> None:
    perfume_response_1 = await async_client.post(
        "/perfumes",
        json={"brand": "Creed", "name": "Aventus", "concentration": "edt"},
    )
    perfume_response_2 = await async_client.post(
        "/perfumes",
        json={"brand": "Tom Ford", "name": "Oud Wood"},
    )

    perfume_1 = perfume_response_1.json()
    perfume_2 = perfume_response_2.json()

    results = await async_client.get("/perfumes")

    assert results.status_code == 200
    data = results.json()

    items_by_id = {item["id"]: item for item in data}
    assert items_by_id == {perfume_1["id"]: perfume_1, perfume_2["id"]: perfume_2}
    assert data == [perfume_1, perfume_2]


@pytest.mark.anyio
async def test_correct_archive_status(async_client: AsyncClient) -> None:
    perfume_response = await async_client.post(
        "/perfumes",
        json={"brand": "Creed", "name": "Aventus", "concentration": "edt"},
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
    wearing_id_1 = wearing_response.json()["id"]

    assert wearing_response.status_code == 201

    archived_item_response = await async_client.patch(
        f"/collection-items/{collection_item_id}", json={"status": "archived"}
    )
    archived_item = archived_item_response.json()

    assert archived_item_response.status_code == 200
    assert archived_item["status"] == "archived"
    assert archived_item["id"] == collection_item_id

    failed_wearing_response = await async_client.post(
        f"/collection-items/{collection_item_id}/wearings",
        json={
            "worn_at": "2026-10-02T09:30:00+03:00",
            "rating": 5,
            "comment": "Test comment",
        },
    )

    assert failed_wearing_response.status_code == 409
    assert (
        failed_wearing_response.json()["detail"]
        == "Cannot add a wearing to an archived collection item."
    )

    details_archived_response = await async_client.get(f"/perfumes/{perfume_id}")
    details_archived = details_archived_response.json()

    assert details_archived_response.status_code == 200
    assert len(details_archived["collection_items"]) == 1
    item_archived = details_archived["collection_items"][0]
    assert item_archived["id"] == collection_item_id
    assert item_archived["status"] == "archived"
    assert item_archived["wearings"][0]["rating"] == 5
    assert item_archived["wearings"][0]["comment"] == "Test comment"
    assert item_archived["wearings"][0]["collection_item_id"] == archived_item["id"]
    assert datetime.fromisoformat(
        item_archived["wearings"][0]["worn_at"]
    ) == datetime.fromisoformat("2026-10-02T09:30:00+03:00")
    assert len(item_archived["wearings"]) == 1
    wearing = item_archived["wearings"][0]

    assert wearing["id"] == wearing_id_1
    assert wearing["rating"] == 5
    assert wearing["comment"] == "Test comment"
    assert datetime.fromisoformat(wearing["worn_at"]) == datetime.fromisoformat(
        "2026-10-02T09:30:00+03:00"
    )

    active_item_response = await async_client.patch(
        f"/collection-items/{collection_item_id}", json={"status": "active"}
    )
    active_item = active_item_response.json()

    assert active_item_response.status_code == 200
    assert active_item == item_response.json()

    wearing_response_2 = await async_client.post(
        f"/collection-items/{collection_item_id}/wearings",
        json={
            "worn_at": "2026-12-03T09:30:00+03:00",
            "rating": 7,
            "comment": "Test comment",
        },
    )
    wearing_id_2 = wearing_response_2.json()["id"]
    assert wearing_response_2.status_code == 201

    details_active_response = await async_client.get(f"/perfumes/{perfume_id}")
    details_active = details_active_response.json()

    assert details_active_response.status_code == 200
    assert len(details_active["collection_items"][0]["wearings"]) == 2

    items_by_id = {
        item["id"]: item for item in details_active["collection_items"][0]["wearings"]
    }
    assert set(items_by_id.keys()) == {wearing_id_1, wearing_id_2}


@pytest.mark.anyio
async def test_archive_item_not_found(async_client: AsyncClient) -> None:
    archive_item_response = await async_client.patch(
        "/collection-items/999", json={"status": "active"}
    )

    assert archive_item_response.status_code == 404
    assert archive_item_response.json()["detail"] == "Collection item not found."


@pytest.mark.anyio
async def test_invalid_item_status(async_client: AsyncClient) -> None:
    perfume_response = await async_client.post(
        "/perfumes",
        json={"brand": "Creed", "name": "Aventus", "concentration": "edt"},
    )
    perfume_id = perfume_response.json()["id"]

    item_response = await async_client.post(
        f"/perfumes/{perfume_id}/collection-items",
        json={"kind": "sample", "initial_volume_ml": 1.5, "acquired_on": "2026-05-09"},
    )
    collection_item_id = item_response.json()["id"]

    archived_item_response = await async_client.patch(
        f"/collection-items/{collection_item_id}", json={"status": "deleted"}
    )

    assert archived_item_response.status_code == 422

    details_active_response = await async_client.get(f"/perfumes/{perfume_id}")
    details_active = details_active_response.json()

    assert details_active["collection_items"][0]["status"] == "active"


@pytest.mark.anyio
async def test_empty_list_collection_items(async_client: AsyncClient) -> None:
    response = await async_client.get(
        "/collection-items", params={"status": "archived"}
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_correct_list_collection_items(async_client: AsyncClient) -> None:
    perfume_response = await async_client.post(
        "/perfumes",
        json={"brand": "Creed", "name": "Aventus", "concentration": "edt"},
    )
    perfume_id = perfume_response.json()["id"]

    item_response_1 = await async_client.post(
        f"/perfumes/{perfume_id}/collection-items",
        json={"kind": "sample", "initial_volume_ml": 1.5, "acquired_on": "2026-05-09"},
    )
    item_response_2 = await async_client.post(
        f"/perfumes/{perfume_id}/collection-items",
        json={"kind": "sample", "initial_volume_ml": 1.5, "acquired_on": "2026-05-09"},
    )
    collection_item_id_2 = item_response_2.json()["id"]

    archived_item_resp = await async_client.patch(
        f"/collection-items/{collection_item_id_2}", json={"status": "archived"}
    )

    active_items_response = await async_client.get("/collection-items")
    assert active_items_response.status_code == 200
    active_items = active_items_response.json()
    assert active_items == [item_response_1.json()]

    archived_items_response = await async_client.get(
        "/collection-items", params={"status": "archived"}
    )
    assert archived_items_response.status_code == 200
    archived_items = archived_items_response.json()
    assert archived_items == [archived_item_resp.json()]


@pytest.mark.anyio
async def test_wrong_status_list_collection_items(async_client: AsyncClient) -> None:
    items_response = await async_client.get(
        "/collection-items", params={"status": "deleted"}
    )

    assert items_response.status_code == 422


@pytest.mark.anyio
async def test_correct_delete_collection_item(async_client: AsyncClient) -> None:
    perfume_response = await async_client.post(
        "/perfumes",
        json={"brand": "Creed", "name": "Aventus", "concentration": "edt"},
    )
    perfume_id = perfume_response.json()["id"]

    item_response = await async_client.post(
        f"/perfumes/{perfume_id}/collection-items",
        json={"kind": "sample", "initial_volume_ml": 1.5, "acquired_on": "2026-05-09"},
    )
    collection_item_id = item_response.json()["id"]

    delete_response = await async_client.delete(
        f"/collection-items/{collection_item_id}"
    )

    assert delete_response.status_code == 204
    assert delete_response.content == b""

    details_response = await async_client.get(f"/perfumes/{perfume_id}")
    details = details_response.json()
    assert details["collection_items"] == []


@pytest.mark.anyio
async def test_delete_collection_item_not_found(async_client: AsyncClient) -> None:
    delete_response = await async_client.delete("/collection-items/999")

    assert delete_response.status_code == 404
    assert delete_response.json()["detail"] == "Collection item not found."


@pytest.mark.anyio
async def test_delete_collection_item_with_wearing(async_client: AsyncClient) -> None:
    perfume_response = await async_client.post(
        "/perfumes",
        json={"brand": "Creed", "name": "Aventus", "concentration": "edt"},
    )
    perfume_id = perfume_response.json()["id"]

    item_response = await async_client.post(
        f"/perfumes/{perfume_id}/collection-items",
        json={"kind": "sample", "initial_volume_ml": 1.5, "acquired_on": "2026-05-09"},
    )
    collection_item_id = item_response.json()["id"]

    await async_client.post(
        f"/collection-items/{collection_item_id}/wearings",
        json={
            "worn_at": "2026-10-02T09:30:00+03:00",
            "rating": 5,
            "comment": "Test comment",
        },
    )

    first_details_response = await async_client.get(f"/perfumes/{perfume_id}")
    first_details = first_details_response.json()

    delete_response_failed = await async_client.delete(
        f"/collection-items/{collection_item_id}"
    )

    assert delete_response_failed.status_code == 409
    assert (
        delete_response_failed.json()["detail"]
        == "Cannot delete a collection item with wearing history."
    )

    second_details_response = await async_client.get(f"/perfumes/{perfume_id}")
    second_details = second_details_response.json()

    assert first_details == second_details


@pytest.mark.anyio
async def test_correct_delete_perfume(async_client: AsyncClient) -> None:
    perfume_response = await async_client.post(
        "/perfumes",
        json={"brand": "Creed", "name": "Aventus", "concentration": "edt"},
    )
    perfume_id = perfume_response.json()["id"]

    delete_response = await async_client.delete(f"/perfumes/{perfume_id}")

    assert delete_response.status_code == 204
    assert delete_response.content == b""

    details_response = await async_client.get(f"/perfumes/{perfume_id}")

    assert details_response.status_code == 404
    assert details_response.json()["detail"] == "Perfume not found."


@pytest.mark.anyio
async def test_delete_perfume_unknown_id(async_client: AsyncClient) -> None:
    delete_response = await async_client.delete("/perfumes/999")

    assert delete_response.status_code == 404
    assert delete_response.json()["detail"] == "Perfume not found."


@pytest.mark.anyio
async def test_failed_delete_perfume_with_collection_item(
    async_client: AsyncClient,
) -> None:
    perfume_response = await async_client.post(
        "/perfumes",
        json={"brand": "Creed", "name": "Aventus", "concentration": "edt"},
    )
    perfume_id = perfume_response.json()["id"]

    await async_client.post(
        f"/perfumes/{perfume_id}/collection-items",
        json={"kind": "sample", "initial_volume_ml": 1.5, "acquired_on": "2026-05-09"},
    )

    details_before_response = await async_client.get(f"/perfumes/{perfume_id}")
    details_before = details_before_response.json()

    delete_response = await async_client.delete(f"/perfumes/{perfume_id}")

    assert delete_response.status_code == 409
    assert (
        delete_response.json()["detail"]
        == "Cannot delete a perfume with collection items."
    )

    details_after_response = await async_client.get(f"/perfumes/{perfume_id}")
    details_after = details_after_response.json()

    assert details_before == details_after
