"""Tests for the Nature Remo config flow."""

from __future__ import annotations

import hashlib
from unittest.mock import AsyncMock, patch

import aiohttp
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
import pytest

from custom_components.nature_remo.const import DOMAIN


def _unique_id(api_key: str) -> str:
    """Compute the unique_id used by the config flow."""
    return hashlib.sha256(api_key.encode()).hexdigest()[:32]


async def test_user_step_valid_api_key(hass):
    """Test async_step_user with a valid API key creates a config entry."""
    with patch(
        "custom_components.nature_remo.config_flow.NatureRemoAPI.get_devices",
        new=AsyncMock(return_value=[{"id": "device-1"}]),
    ), patch(
        "custom_components.nature_remo.async_setup_entry",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {}

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"name": "Nature Remo", "api_key": "valid_key"},
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Nature Remo"
    assert result["data"] == {"api_key": "valid_key"}

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].unique_id == _unique_id("valid_key")


async def test_user_step_invalid_api_key(hass):
    """Test async_step_user with an invalid API key shows an error."""
    with patch(
        "custom_components.nature_remo.config_flow.NatureRemoAPI.get_devices",
        new=AsyncMock(side_effect=aiohttp.ClientError("Unauthorized")),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"name": "Nature Remo", "api_key": "invalid_key"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "invalid_auth"}


async def test_reauth_step_valid_api_key(hass):
    """Test async_step_reauth with a valid API key updates the entry and reloads."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    old_key = "old_api_key"
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"api_key": old_key},
        unique_id=_unique_id(old_key),
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.nature_remo.config_flow.NatureRemoAPI.get_devices",
        new=AsyncMock(return_value=[{"id": "device-1"}]),
    ), patch.object(
        hass.config_entries, "async_reload", new=AsyncMock()
    ) as mock_reload:
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_REAUTH,
                "entry_id": entry.entry_id,
            },
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "reauth"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"api_key": "new_api_key"},
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data == {"api_key": "new_api_key"}
    mock_reload.assert_awaited_once_with(entry.entry_id)


async def test_reauth_step_invalid_api_key(hass):
    """Test async_step_reauth with an invalid API key shows an error."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    old_key = "old_api_key"
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"api_key": old_key},
        unique_id=_unique_id(old_key),
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.nature_remo.config_flow.NatureRemoAPI.get_devices",
        new=AsyncMock(side_effect=aiohttp.ClientError("Unauthorized")),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_REAUTH,
                "entry_id": entry.entry_id,
            },
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"api_key": "bad_key"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reauth"
    assert result["errors"] == {"base": "invalid_auth"}


async def test_unique_id_conflict(hass):
    """Test that a duplicate unique_id aborts the user flow."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    api_key = "my_api_key"
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"api_key": api_key},
        unique_id=_unique_id(api_key),
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"name": "Nature Remo", "api_key": api_key},
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
