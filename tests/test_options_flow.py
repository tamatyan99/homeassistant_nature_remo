"""Tests for the Nature Remo options flow."""

from __future__ import annotations

import hashlib
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nature_remo.const import DOMAIN


def _unique_id(api_key: str) -> str:
    """Compute the unique_id used by the config flow."""
    return hashlib.sha256(api_key.encode()).hexdigest()[:32]


@pytest.fixture
async def init_integration(hass: HomeAssistant):
    """Set up the Nature Remo integration for tests."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"api_key": "test_key"},
        unique_id=_unique_id("test_key"),
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.nature_remo.async_setup_entry",
        return_value=True,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


@pytest.mark.usefixtures("init_integration")
async def test_options_flow_init(hass: HomeAssistant, init_integration):
    """Test options flow initialization."""
    entry = init_integration
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"
