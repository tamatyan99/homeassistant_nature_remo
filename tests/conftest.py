"""Shared test fixtures for the Nature Remo integration."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.nature_remo.api import NatureRemoAPI


@pytest.fixture
async def api() -> NatureRemoAPI:
    """Return a NatureRemoAPI instance with a mocked session."""
    return NatureRemoAPI("test-token")


@pytest.fixture
def mock_session() -> Generator[MagicMock]:
    """Patch aiohttp.ClientSession for API tests."""
    with patch("aiohttp.ClientSession") as mock_cls:
        session = MagicMock()
        mock_cls.return_value = session
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        yield session


def mock_response(
    status: int = 200,
    json_data: dict | list | None = None,
    text: str = "",
    headers: dict | None = None,
) -> MagicMock:
    """Build a mocked aiohttp response."""
    response = MagicMock()
    response.status = status
    response.headers = headers or {}
    response.json = AsyncMock(return_value=json_data if json_data is not None else {})
    response.text = AsyncMock(return_value=text)
    return response
