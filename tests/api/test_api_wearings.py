import pytest
from httpx2 import AsyncClient


@pytest.mark.anyio
async def test_create_wearing(async_client: AsyncClient) -> None:
    perfume_response = await async_client.post(
        "/perfumes", json={"brand": "Creed", "name": "Aventus", "concentration": "edp"}
    )
    assert perfume_response.status_code == 201
    perfume_id = perfume_response.json()["id"]

    item_response = await async_client.post(
        f"/perfumes/{perfume_id}/collection-items",
        json={"kind": "sample", "initial_volume_ml": 1.5, "acquired_on": "2026-05-09"},
    )
    assert item_response.status_code == 201
    collection_item_id = item_response.json()["id"]

    response = await async_client.post(
        f"/collection-items/{collection_item_id}/wearings",
        json={
            "worn_at": "2026-10-02T09:30:00+03:00",
            "rating": 5,
            "comment": "Test comment",
        },
    )

    assert response.status_code == 201
    wearing = response.json()

    assert wearing["id"] > 0
    assert wearing["collection_item_id"] == collection_item_id
    assert wearing["worn_at"] == "2026-10-02T06:30:00Z"
    assert wearing["rating"] == 5
    assert wearing["comment"] == "Test comment"


@pytest.mark.anyio
async def test_create_wearing_missing_collection_item_returns_404(
    async_client: AsyncClient,
) -> None:
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
async def test_create_wearing_invalid_body_returns_422(
    async_client: AsyncClient,
) -> None:
    perfume_response = await async_client.post(
        "/perfumes", json={"brand": "Creed", "name": "Aventus", "concentration": "edp"}
    )
    assert perfume_response.status_code == 201
    perfume_id = perfume_response.json()["id"]

    item_response = await async_client.post(
        f"/perfumes/{perfume_id}/collection-items",
        json={"kind": "sample", "initial_volume_ml": 1.5, "acquired_on": "2026-05-09"},
    )
    assert item_response.status_code == 201
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
async def test_list_wearings_filter_by_date(async_client: AsyncClient) -> None:
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

    wearing_response_1 = await async_client.post(
        f"/collection-items/{collection_item_id}/wearings",
        json={"worn_at": "2026-10-28T10:00:00+03:00", "rating": 8},
    )
    assert wearing_response_1.status_code == 201
    wearing_1 = wearing_response_1.json()

    wearing_response_2 = await async_client.post(
        f"/collection-items/{collection_item_id}/wearings",
        json={"worn_at": "2026-11-01T12:00:00+03:00", "rating": 9},
    )
    assert wearing_response_2.status_code == 201
    wearing_2 = wearing_response_2.json()

    wearing_response_3 = await async_client.post(
        f"/collection-items/{collection_item_id}/wearings",
        json={"worn_at": "2026-11-05T10:00:00+03:00", "rating": 7},
    )
    assert wearing_response_3.status_code == 201

    params = {
        "worn_from": "2026-10-28T10:00:00+03:00",
        "worn_before": "2026-11-05T10:00:00+03:00",
    }
    response = await async_client.get(
        f"/collection-items/{collection_item_id}/wearings",
        params=params,
    )
    assert response.status_code == 200
    results = response.json()

    assert len(results) == 2
    assert [item["id"] for item in results] == [wearing_2["id"], wearing_1["id"]]
    items_by_id = {item["id"]: item for item in results}
    row1 = items_by_id[wearing_1["id"]]
    row2 = items_by_id[wearing_2["id"]]

    assert row1["rating"] == 8
    assert row1["comment"] is None
    assert row1["collection_item_id"] == collection_item_id
    assert row1["worn_at"] == "2026-10-28T07:00:00Z"

    assert row2["rating"] == 9
    assert row2["comment"] is None
    assert row2["collection_item_id"] == collection_item_id
    assert row2["worn_at"] == "2026-11-01T09:00:00Z"


@pytest.mark.anyio
async def test_list_wearings_naive_datetime_returns_422(
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

    params = {"worn_from": "2026-11-05T00:00:00"}
    response = await async_client.get(
        f"/collection-items/{collection_item_id}/wearings",
        params=params,
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_list_wearings_invalid_range_returns_422(
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

    params = {
        "worn_from": "2026-11-05T10:00:00+03:00",
        "worn_before": "2026-10-28T10:00:00+03:00",
    }
    response = await async_client.get(
        f"/collection-items/{collection_item_id}/wearings",
        params=params,
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_list_wearings_missing_item_returns_404(
    async_client: AsyncClient,
) -> None:
    response = await async_client.get("/collection-items/999/wearings")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_delete_wearing(
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
    wearing_id = wearing_response.json()["id"]

    patch_response = await async_client.patch(
        f"/collection-items/{collection_item_id}", json={"status": "archived"}
    )
    assert patch_response.status_code == 200

    delete_wearing_response = await async_client.delete(f"/wearings/{wearing_id}")

    assert delete_wearing_response.status_code == 204
    assert delete_wearing_response.content == b""

    details_response = await async_client.get(f"/perfumes/{perfume_id}")
    assert details_response.status_code == 200
    details = details_response.json()

    assert details["collection_items"][0]["status"] == "archived"
    assert details["collection_items"][0]["wearings"] == []
    assert details["average_rating"] is None

    failed_delete_response = await async_client.delete(f"/wearings/{wearing_id}")
    assert failed_delete_response.status_code == 404
    assert failed_delete_response.json()["detail"] == "Wearing not found."


@pytest.mark.anyio
async def test_delete_missing_wearing_returns_404(
    async_client: AsyncClient,
) -> None:
    delete_response = await async_client.delete("/wearings/999")
    assert delete_response.status_code == 404
    assert delete_response.json()["detail"] == "Wearing not found."


@pytest.mark.anyio
async def test_get_wearing_by_id(
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
    wearing_id = wearing_response.json()["id"]

    another_weraing_response = await async_client.post(
        f"/collection-items/{collection_item_id}/wearings",
        json={
            "worn_at": "2026-10-02T09:30:00+03:00",
            "rating": 10,
            "comment": "Test comment",
        },
    )
    assert another_weraing_response.status_code == 201

    target_wearing_response = await async_client.get(f"/wearings/{wearing_id}")

    assert target_wearing_response.status_code == 200
    assert target_wearing_response.json() == {
        "id": wearing_id,
        "collection_item_id": collection_item_id,
        "worn_at": "2026-10-02T06:30:00Z",
        "rating": 5,
        "comment": "Test comment",
    }


@pytest.mark.anyio
async def test_get_missing_wearing_returns_404(
    async_client: AsyncClient,
) -> None:
    get_wearing_response = await async_client.get("/wearings/999")

    assert get_wearing_response.status_code == 404
    assert get_wearing_response.json()["detail"] == "Wearing not found."
