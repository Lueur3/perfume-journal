from typing import Any

import pytest
from httpx2 import AsyncClient


@pytest.mark.anyio
async def test_create_perfume_successful(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/perfumes", json={"brand": "Creed", "name": "Aventus", "concentration": "edp"}
    )
    assert response.status_code == 201

    data = response.json()
    assert data["brand"] == "Creed"
    assert data["name"] == "Aventus"
    assert data["concentration"] == "EDP"
    assert data["id"] > 0


@pytest.mark.anyio
async def test_create_duplicate_perfume_returns_409(async_client: AsyncClient) -> None:
    initial_response = await async_client.post(
        "/perfumes", json={"brand": "Creed", "name": "Aventus", "concentration": "edp"}
    )
    assert initial_response.status_code == 201

    response = await async_client.post(
        "/perfumes",
        json={"brand": "creed", "name": "AVENTUS", "concentration": "EDP"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "This perfume already exists."


@pytest.mark.anyio
async def test_create_perfume_invalid_body_returns_422(
    async_client: AsyncClient,
) -> None:
    response = await async_client.post(
        "/perfumes", json={"brand": " ", "name": "Aventus"}
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_get_perfume_details(async_client: AsyncClient) -> None:
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

    response = await async_client.get(f"/perfumes/{perfume_id}")
    assert response.status_code == 200

    details = response.json()
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
    assert (
        details["collection_items"][0]["wearings"][0]["worn_at"]
        == "2026-10-02T06:30:00Z"
    )
    assert details["collection_items"][0]["wearings"][0]["rating"] == 5
    assert details["collection_items"][0]["wearings"][0]["comment"] == "Test comment"


@pytest.mark.anyio
async def test_get_missing_perfume_returns_404(async_client: AsyncClient) -> None:
    response = await async_client.get("/perfumes/1")

    assert response.status_code == 404
    assert response.json()["detail"] == "Perfume not found."


@pytest.mark.anyio
async def test_update_perfume(async_client: AsyncClient) -> None:
    perfume_response = await async_client.post(
        "/perfumes", json={"brand": "Creed", "name": "Aventus", "concentration": "edp"}
    )
    assert perfume_response.status_code == 201
    perfume_id = perfume_response.json()["id"]

    response = await async_client.put(
        f"/perfumes/{perfume_id}",
        json={"brand": "Tom Ford", "name": "Oud Wood", "concentration": "edt"},
    )
    assert response.status_code == 200
    item = response.json()

    assert item["id"] == perfume_id
    assert item["brand"] == "Tom Ford"
    assert item["name"] == "Oud Wood"
    assert item["concentration"] == "EDT"

    response_get = await async_client.get(f"/perfumes/{perfume_id}")
    assert response_get.status_code == 200
    item_get = response_get.json()

    assert item_get["id"] == perfume_id
    assert item_get["brand"] == "Tom Ford"
    assert item_get["name"] == "Oud Wood"
    assert item_get["concentration"] == "EDT"


@pytest.mark.anyio
async def test_update_missing_perfume_returns_404(async_client: AsyncClient) -> None:
    response = await async_client.put(
        "/perfumes/1",
        json={"brand": "Tom Ford", "name": "Oud Wood", "concentration": "edt"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Perfume not found."


@pytest.mark.anyio
async def test_update_perfume_duplicate_returns_409(async_client: AsyncClient) -> None:
    existing_response = await async_client.post(
        "/perfumes", json={"brand": "Creed", "name": "Aventus", "concentration": "edp"}
    )
    assert existing_response.status_code == 201

    target_response = await async_client.post(
        "/perfumes",
        json={"brand": "Tom Ford", "name": "Oud Wood", "concentration": "edt"},
    )
    assert target_response.status_code == 201
    target_perfume_id = target_response.json()["id"]

    response = await async_client.put(
        f"/perfumes/{target_perfume_id}",
        json={"brand": "Creed", "name": "Aventus", "concentration": "edp"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "This perfume already exists."


@pytest.mark.anyio
async def test_update_perfume_invalid_body_returns_422(
    async_client: AsyncClient,
) -> None:
    perfume_response = await async_client.post(
        "/perfumes",
        json={"brand": "Tom Ford", "name": "Oud Wood", "concentration": "edt"},
    )
    assert perfume_response.status_code == 201
    perfume_id = perfume_response.json()["id"]

    response = await async_client.put(
        f"/perfumes/{perfume_id}",
        json={"brand": "  ", "name": "Aventus", "concentration": "edp"},
    )

    assert response.status_code == 422

    response_get = await async_client.get(f"/perfumes/{perfume_id}")
    assert response_get.status_code == 200
    item_get = response_get.json()

    assert item_get["id"] == perfume_id
    assert item_get["brand"] == "Tom Ford"
    assert item_get["name"] == "Oud Wood"
    assert item_get["concentration"] == "EDT"


@pytest.mark.anyio
async def test_update_perfume_preserves_collection_items_and_rating(
    async_client: AsyncClient,
) -> None:
    perfume_response = await async_client.post(
        "/perfumes",
        json={"brand": "Tom Ford", "name": "Oud Wood", "concentration": "edt"},
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

    archive_response = await async_client.patch(
        f"/collection-items/{collection_item_id}", json={"status": "archived"}
    )
    assert archive_response.status_code == 200

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
async def test_list_perfumes_empty(async_client: AsyncClient) -> None:
    results = await async_client.get("/perfumes")

    assert results.status_code == 200
    assert results.json() == []


@pytest.mark.anyio
async def test_list_perfumes(async_client: AsyncClient) -> None:
    perfume_response_1 = await async_client.post(
        "/perfumes",
        json={"brand": "Creed", "name": "Aventus", "concentration": "edt"},
    )
    assert perfume_response_1.status_code == 201
    perfume_1 = perfume_response_1.json()

    perfume_response_2 = await async_client.post(
        "/perfumes",
        json={"brand": "Tom Ford", "name": "Oud Wood"},
    )
    assert perfume_response_2.status_code == 201
    perfume_2 = perfume_response_2.json()

    results = await async_client.get("/perfumes")

    assert results.status_code == 200
    data = results.json()

    assert data == [perfume_1, perfume_2]


@pytest.mark.anyio
async def test_list_perfumes_search(async_client: AsyncClient) -> None:
    aventus_response = await async_client.post(
        "/perfumes",
        json={"brand": "Creed", "name": "Aventus", "concentration": "edt"},
    )
    assert aventus_response.status_code == 201
    expected_perfume = aventus_response.json()

    tom_ford_response = await async_client.post(
        "/perfumes",
        json={"brand": "Tom Ford", "name": "Oud Wood"},
    )
    assert tom_ford_response.status_code == 201

    response = await async_client.get("/perfumes", params={"q": "AVEN"})

    assert response.status_code == 200
    assert response.json() == [expected_perfume]


@pytest.mark.anyio
async def test_list_perfumes_search_no_matches(async_client: AsyncClient) -> None:
    perfume_response_1 = await async_client.post(
        "/perfumes",
        json={"brand": "Creed", "name": "Aventus", "concentration": "edt"},
    )
    assert perfume_response_1.status_code == 201

    perfume_response_2 = await async_client.post(
        "/perfumes",
        json={"brand": "Tom Ford", "name": "Oud Wood"},
    )
    assert perfume_response_2.status_code == 201

    response = await async_client.get("/perfumes", params={"q": "Dior"})

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_delete_perfume(async_client: AsyncClient) -> None:
    perfume_response = await async_client.post(
        "/perfumes",
        json={"brand": "Creed", "name": "Aventus", "concentration": "edt"},
    )
    assert perfume_response.status_code == 201
    perfume_id = perfume_response.json()["id"]

    delete_response = await async_client.delete(f"/perfumes/{perfume_id}")

    assert delete_response.status_code == 204
    assert delete_response.content == b""

    details_response = await async_client.get(f"/perfumes/{perfume_id}")

    assert details_response.status_code == 404
    assert details_response.json()["detail"] == "Perfume not found."


@pytest.mark.anyio
async def test_delete_missing_perfume_returns_404(
    async_client: AsyncClient,
) -> None:
    delete_response = await async_client.delete("/perfumes/999")

    assert delete_response.status_code == 404
    assert delete_response.json()["detail"] == "Perfume not found."


@pytest.mark.anyio
async def test_delete_perfume_with_collection_items_returns_409(
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

    details_before_response = await async_client.get(f"/perfumes/{perfume_id}")
    assert details_before_response.status_code == 200
    details_before = details_before_response.json()

    delete_response = await async_client.delete(f"/perfumes/{perfume_id}")

    assert delete_response.status_code == 409
    assert (
        delete_response.json()["detail"]
        == "Cannot delete a perfume with collection items."
    )

    details_after_response = await async_client.get(f"/perfumes/{perfume_id}")
    assert details_after_response.status_code == 200
    details_after = details_after_response.json()

    assert details_before == details_after


@pytest.mark.anyio
async def test_update_perfume_source_partial_update_returns_200(
    async_client: AsyncClient,
) -> None:
    perfume_response = await async_client.post(
        "/perfumes",
        json={"brand": "Creed", "name": "Aventus", "concentration": "edt"},
    )
    assert perfume_response.status_code == 201
    perfume_id = perfume_response.json()["id"]

    source_response = await async_client.patch(
        f"/perfumes/{perfume_id}/source",
        json={"sillage": "arms_length", "url": "https://example.com"},
    )
    assert source_response.status_code == 200
    source_data = source_response.json()

    new_source_response = await async_client.patch(
        f"/perfumes/{perfume_id}/source",
        json={"sillage": "fills_room"},
    )
    assert new_source_response.status_code == 200
    new_source_data = new_source_response.json()

    assert new_source_data["sillage"] == "fills_room"
    assert new_source_data["url"] == source_data["url"]


@pytest.mark.anyio
async def test_update_perfume_source_null_clears_field_returns_200(
    async_client: AsyncClient,
) -> None:
    perfume_response = await async_client.post(
        "/perfumes",
        json={"brand": "Creed", "name": "Aventus", "concentration": "edt"},
    )
    assert perfume_response.status_code == 201
    perfume_id = perfume_response.json()["id"]

    source_response = await async_client.patch(
        f"/perfumes/{perfume_id}/source",
        json={"url": "https://example.com"},
    )
    assert source_response.status_code == 200

    new_source_response = await async_client.patch(
        f"/perfumes/{perfume_id}/source",
        json={"url": None},
    )
    assert new_source_response.status_code == 200
    new_source_data = new_source_response.json()

    assert new_source_data["url"] is None


@pytest.mark.anyio
async def test_update_perfume_source_missing_perfume_returns_404(
    async_client: AsyncClient,
) -> None:
    source_response = await async_client.patch(
        "/perfumes/999/source",
        json={"url": "https://example.com"},
    )

    assert source_response.status_code == 404
    assert source_response.json()["detail"] == "Perfume not found."


@pytest.mark.anyio
@pytest.mark.parametrize(
    "invalid_payload",
    [
        {"seasons": 123},
        {"sillage": "invalid"},
        {"seasons": ["monsoon"]},
        {"url": "not-a-url"},
    ],
)
async def test_update_perfume_source_invalid_body_returns_422(
    async_client: AsyncClient, invalid_payload: dict[str, Any]
) -> None:
    perfume_response = await async_client.post(
        "/perfumes",
        json={"brand": "Creed", "name": "Aventus", "concentration": "edt"},
    )
    assert perfume_response.status_code == 201
    perfume_id = perfume_response.json()["id"]

    source_response = await async_client.patch(
        f"/perfumes/{perfume_id}/source",
        json=invalid_payload,
    )

    assert source_response.status_code == 422


@pytest.mark.anyio
async def test_update_perfume_personal_partial_update_returns_200(
    async_client: AsyncClient,
) -> None:
    perfume_response = await async_client.post(
        "/perfumes",
        json={"brand": "Creed", "name": "Aventus", "concentration": "edt"},
    )
    assert perfume_response.status_code == 201
    perfume_id = perfume_response.json()["id"]

    personal_response = await async_client.patch(
        f"/perfumes/{perfume_id}/personal",
        json={
            "sillage": "arms_length",
            "longevity_hours": 6.5,
            "comment": "Initial impression",
        },
    )
    assert personal_response.status_code == 200
    personal_data = personal_response.json()

    new_personal_response = await async_client.patch(
        f"/perfumes/{perfume_id}/personal",
        json={"sillage": "fills_room"},
    )
    assert new_personal_response.status_code == 200
    new_personal_data = new_personal_response.json()

    assert new_personal_data["sillage"] == "fills_room"
    assert new_personal_data["longevity_hours"] == personal_data["longevity_hours"]
    assert new_personal_data["comment"] == personal_data["comment"]


@pytest.mark.anyio
async def test_update_perfume_personal_null_clears_field_returns_200(
    async_client: AsyncClient,
) -> None:
    perfume_response = await async_client.post(
        "/perfumes",
        json={"brand": "Creed", "name": "Aventus", "concentration": "edt"},
    )
    assert perfume_response.status_code == 201
    perfume_id = perfume_response.json()["id"]

    personal_response = await async_client.patch(
        f"/perfumes/{perfume_id}/personal",
        json={"comment": "Temporary note"},
    )
    assert personal_response.status_code == 200

    new_personal_response = await async_client.patch(
        f"/perfumes/{perfume_id}/personal",
        json={"comment": None},
    )
    assert new_personal_response.status_code == 200
    new_personal_data = new_personal_response.json()

    assert new_personal_data["comment"] is None


@pytest.mark.anyio
async def test_update_perfume_personal_missing_perfume_returns_404(
    async_client: AsyncClient,
) -> None:
    personal_response = await async_client.patch(
        "/perfumes/999/personal",
        json={"comment": "Not found test"},
    )

    assert personal_response.status_code == 404
    assert personal_response.json()["detail"] == "Perfume not found."


@pytest.mark.anyio
@pytest.mark.parametrize(
    "invalid_payload",
    [
        {"longevity_hours": "not_a_number"},
        {"longevity_hours": 0.0},
        {"longevity_hours": 25.0},
        {"sillage": "invalid"},
        {"seasons": ["monsoon"]},
    ],
)
async def test_update_perfume_personal_invalid_body_returns_422(
    async_client: AsyncClient, invalid_payload: dict[str, Any]
) -> None:
    perfume_response = await async_client.post(
        "/perfumes",
        json={"brand": "Creed", "name": "Aventus", "concentration": "edt"},
    )
    assert perfume_response.status_code == 201
    perfume_id = perfume_response.json()["id"]

    personal_response = await async_client.patch(
        f"/perfumes/{perfume_id}/personal",
        json=invalid_payload,
    )

    assert personal_response.status_code == 422


@pytest.mark.anyio
async def test_update_perfume_source_and_personal_isolation_in_details_returns_200(
    async_client: AsyncClient,
) -> None:
    create_response = await async_client.post(
        "/perfumes",
        json={"brand": "Creed", "name": "Aventus", "concentration": "edt"},
    )
    assert create_response.status_code == 201
    perfume_id = create_response.json()["id"]

    source_patch_response = await async_client.patch(
        f"/perfumes/{perfume_id}/source",
        json={"sillage": "arms_length", "longevity": "moderate"},
    )
    assert source_patch_response.status_code == 200

    personal_patch_response = await async_client.patch(
        f"/perfumes/{perfume_id}/personal",
        json={"sillage": "none", "longevity": "long", "longevity_hours": 8.0},
    )
    assert personal_patch_response.status_code == 200

    details_response = await async_client.get(f"/perfumes/{perfume_id}")
    assert details_response.status_code == 200
    details = details_response.json()

    assert details["source"]["sillage"] == "arms_length"
    assert details["source"]["longevity"] == "moderate"
    assert details["personal"]["sillage"] == "none"
    assert details["personal"]["longevity"] == "long"
    assert details["personal"]["longevity_hours"] == 8.0
