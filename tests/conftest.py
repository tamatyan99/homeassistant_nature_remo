"""Shared fixtures for Nature Remo tests."""

from unittest.mock import Mock, patch

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    return enable_custom_integrations


@pytest.fixture(autouse=True)
def mock_async_resolver():
    """Prevent aiodns/pycares from starting a background thread."""
    with patch(
        "homeassistant.helpers.aiohttp_client.AsyncResolver", return_value=Mock()
    ):
        yield
