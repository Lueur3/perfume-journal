from collections.abc import AsyncGenerator

import pytest
from httpx2 import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from perfume_journal import api
from perfume_journal.dependencies import get_session_factory


@pytest.fixture
async def async_client(
    monkeypatch: pytest.MonkeyPatch, session_factory: async_sessionmaker[AsyncSession]
) -> AsyncGenerator[AsyncClient]:
    def override_session_factory() -> async_sessionmaker[AsyncSession]:
        return session_factory

    monkeypatch.setitem(
        api.app.dependency_overrides,
        get_session_factory,
        override_session_factory,
    )

    async with AsyncClient(
        transport=ASGITransport(app=api.app),
        base_url="http://test",
    ) as async_client:
        yield async_client
