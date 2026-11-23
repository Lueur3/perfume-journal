from datetime import datetime

import pytest
from httpx2 import AsyncClient


@pytest.mark.anyio
async def test_creates_collection_item_for_existing_perfume(
    async_client: AsyncClient,
) -> None:
    perfume_response = await async_client.post(
        "/perfumes", json={"brand": "Creed", "name": "Aventus", "concentration": "edp"}
    )
    assert perfume_response.status_code == 201
    perfume_id = perfume_response.json()["id"]

    response = await async_client.post(
        f"/perfumes/{perfume_id}/collection-items",
        json={"kind": "sample", "initial_volume_ml": 1.5, "acquired_on": "2026-05-09"},
    )

    assert response.status_code == 201
    item = response.json()

    assert item["id"] > 0
    assert item["perfume_id"] == perfume_id
    assert item["status"] == "active"
    assert item["kind"] == "sample"
    assert item["initial_volume_ml"] == 1.5
    assert item["acquired_on"] == "2026-05-09"


@pytest.mark.anyio
async def test_create_collection_item_missing_perfume_returns_404(
    async_client: AsyncClient,
) -> None:
    wrong_id = 1

    response = await async_client.post(
        f"/perfumes/{wrong_id}/collection-items",
        json={"kind": "sample", "initial_volume_ml": 1.5, "acquired_on": "2026-05-09"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Perfume not found."


@pytest.mark.anyio
async def test_create_collection_item_invalid_body_returns_422(
    async_client: AsyncClient,
) -> None:
    perfume_response = await async_client.post(
        "/perfumes", json={"brand": "Creed", "name": "Aventus", "concentration": "edp"}
    )
    assert perfume_response.status_code == 201
    perfume_id = perfume_response.json()["id"]

    response = await async_client.post(
        f"/perfumes/{perfume_id}/collection-items",
        json={"kind": "sample", "initial_volume_ml": -1.5, "acquired_on": "2026-05-09"},
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_archive_and_restore_collection_item(async_client: AsyncClient) -> None:
    perfume_response = await async_client.post(
        "/perfumes",
        json={"brand": "Creed", "name": "Aventus", "concentration": "edt"},
    )
    assert perfume_response.status_code == 201
    perfume_id = perfume_response.json()["id"]

    item_response = await async_client.post(
        f"/perfumes/{perfume_id}/collection-items",
        json={"kind": "sample", "initial_volume_ml": 1.5, "acquired_on": "2026-05-09"},
    )
    assert item_response.status_code == 201
    collection_item_id = item_response.json()["id"]

    wearing_response = await async_client.post(
        f"/collection-items/{collection_item_id}/wearings",
        json={
            "worn_at": "2026-10-02T09:30:00+03:00",
            "rating": 5,
            "comment": "Test comment",
        },
    )
    assert wearing_response.status_code == 201
    wearing_id_1 = wearing_response.json()["id"]

    archived_item_response = await async_client.patch(
        f"/collection-items/{collection_item_id}", json={"status": "archived"}
    )
    assert archived_item_response.status_code == 200
    archived_item = archived_item_response.json()

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
    assert details_archived_response.status_code == 200
    details_archived = details_archived_response.json()

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
    assert active_item_response.status_code == 200
    active_item = active_item_response.json()
    assert active_item == item_response.json()

    wearing_response_2 = await async_client.post(
        f"/collection-items/{collection_item_id}/wearings",
        json={
            "worn_at": "2026-12-03T09:30:00+03:00",
            "rating": 7,
            "comment": "Test comment",
        },
    )
    assert wearing_response_2.status_code == 201
    wearing_id_2 = wearing_response_2.json()["id"]

    details_active_response = await async_client.get(f"/perfumes/{perfume_id}")
    assert details_active_response.status_code == 200
    details_active = details_active_response.json()

    assert len(details_active["collection_items"][0]["wearings"]) == 2

    items_by_id = {
        item["id"]: item for item in details_active["collection_items"][0]["wearings"]
    }
    assert set(items_by_id.keys()) == {wearing_id_1, wearing_id_2}


@pytest.mark.anyio
async def test_set_collection_item_status_missing_item_returns_404(
    async_client: AsyncClient,
) -> None:
    archive_item_response = await async_client.patch(
        "/collection-items/999", json={"status": "active"}
    )

    assert archive_item_response.status_code == 404
    assert archive_item_response.json()["detail"] == "Collection item not found."


@pytest.mark.anyio
async def test_set_collection_item_status_invalid_returns_422(
    async_client: AsyncClient,
) -> None:
    perfume_response = await async_client.post(
        "/perfumes",
        json={"brand": "Creed", "name": "Aventus", "concentration": "edt"},
    )
    assert perfume_response.status_code == 201
    perfume_id = perfume_response.json()["id"]

    item_response = await async_client.post(
        f"/perfumes/{perfume_id}/collection-items",
        json={"kind": "sample", "initial_volume_ml": 1.5, "acquired_on": "2026-05-09"},
    )
    assert item_response.status_code == 201
    collection_item_id = item_response.json()["id"]

    archived_item_response = await async_client.patch(
        f"/collection-items/{collection_item_id}", json={"status": "deleted"}
    )

    assert archived_item_response.status_code == 422

    details_active_response = await async_client.get(f"/perfumes/{perfume_id}")
    assert details_active_response.status_code == 200
    details_active = details_active_response.json()

    assert details_active["collection_items"][0]["status"] == "active"


@pytest.mark.anyio
async def test_list_collection_items_empty(async_client: AsyncClient) -> None:
    response = await async_client.get(
        "/collection-items", params={"status": "archived"}
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_list_collection_items_filters_by_status(
    async_client: AsyncClient,
) -> None:
    perfume_response = await async_client.post(
        "/perfumes",
        json={"brand": "Creed", "name": "Aventus", "concentration": "edt"},
    )
    assert perfume_response.status_code == 201
    perfume_id = perfume_response.json()["id"]

    item_response_1 = await async_client.post(
        f"/perfumes/{perfume_id}/collection-items",
        json={"kind": "sample", "initial_volume_ml": 1.5, "acquired_on": "2026-05-09"},
    )
    assert item_response_1.status_code == 201

    item_response_2 = await async_client.post(
        f"/perfumes/{perfume_id}/collection-items",
        json={"kind": "sample", "initial_volume_ml": 1.5, "acquired_on": "2026-05-09"},
    )
    assert item_response_2.status_code == 201
    collection_item_id_2 = item_response_2.json()["id"]

    archived_item_resp = await async_client.patch(
        f"/collection-items/{collection_item_id_2}", json={"status": "archived"}
    )
    assert archived_item_resp.status_code == 200

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
async def test_list_collection_items_invalid_status_returns_422(
    async_client: AsyncClient,
) -> None:
    items_response = await async_client.get(
        "/collection-items", params={"status": "deleted"}
    )

    assert items_response.status_code == 422


@pytest.mark.anyio
async def test_delete_collection_item(async_client: AsyncClient) -> None:
    perfume_response = await async_client.post(
        "/perfumes",
        json={"brand": "Creed", "name": "Aventus", "concentration": "edt"},
    )
    assert perfume_response.status_code == 201
    perfume_id = perfume_response.json()["id"]

    item_response = await async_client.post(
        f"/perfumes/{perfume_id}/collection-items",
        json={"kind": "sample", "initial_volume_ml": 1.5, "acquired_on": "2026-05-09"},
    )
    assert item_response.status_code == 201
    collection_item_id = item_response.json()["id"]

    delete_response = await async_client.delete(
        f"/collection-items/{collection_item_id}"
    )

    assert delete_response.status_code == 204
    assert delete_response.content == b""

    details_response = await async_client.get(f"/perfumes/{perfume_id}")
    assert details_response.status_code == 200
    details = details_response.json()
    assert details["collection_items"] == []


@pytest.mark.anyio
async def test_delete_missing_collection_item_returns_404(
    async_client: AsyncClient,
) -> None:
    delete_response = await async_client.delete("/collection-items/999")

    assert delete_response.status_code == 404
    assert delete_response.json()["detail"] == "Collection item not found."


@pytest.mark.anyio
async def test_delete_collection_item_with_wearings_returns_409(
    async_client: AsyncClient,
) -> None:
    perfume_response = await async_client.post(
        "/perfumes",
        json={"brand": "Creed", "name": "Aventus", "concentration": "edt"},
    )
    assert perfume_response.status_code == 201
    perfume_id = perfume_response.json()["id"]

    item_response = await async_client.post(
        f"/perfumes/{perfume_id}/collection-items",
        json={"kind": "sample", "initial_volume_ml": 1.5, "acquired_on": "2026-05-09"},
    )
    assert item_response.status_code == 201
    collection_item_id = item_response.json()["id"]

    wearing_response = await async_client.post(
        f"/collection-items/{collection_item_id}/wearings",
        json={
            "worn_at": "2026-10-02T09:30:00+03:00",
            "rating": 5,
            "comment": "Test comment",
        },
    )
    assert wearing_response.status_code == 201

    first_details_response = await async_client.get(f"/perfumes/{perfume_id}")
    assert first_details_response.status_code == 200
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
    assert second_details_response.status_code == 200
    second_details = second_details_response.json()

    assert first_details == second_details
