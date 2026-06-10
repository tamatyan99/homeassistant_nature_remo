"""Tests for the Nature Remo switch platform."""

from unittest.mock import AsyncMock

import pytest
from aiohttp import ClientError
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from custom_components.nature_remo.api import NatureRemoAuthError


async def test_switch_async_setup_entry_creates_entity(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that async_setup_entry creates the switch entity."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    state = hass.states.get("switch.living_room")
    assert state is not None


async def test_switch_entity_properties(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test switch entity properties."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    entity_reg = er.async_get(hass)
    entity = entity_reg.async_get("switch.living_room")
    assert entity is not None
    assert entity.unique_id == "nature_remo_switch_remote-1"

    state = hass.states.get("switch.living_room")
    assert state.state == "off"
    assert state.attributes["icon"] == "mdi:remote"


async def test_switch_coordinator_update_changes_commands(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that coordinator update refreshes available commands."""
    entry = await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    new_appliances = [dict(a) for a in coordinator_data["appliances"]]
    for app in new_appliances:
        if app["id"] == "remote-1":
            app["signals"] = [
                {"id": "sig-on", "name": "on"},
                {"id": "sig-off", "name": "off"},
                {"id": "sig-input", "name": "input"},
            ]

    mock_api.get_devices = AsyncMock(return_value=coordinator_data["devices"])
    mock_api.get_appliances = AsyncMock(return_value=new_appliances)

    await hass.data["nature_remo"][entry.entry_id]["coordinator"].async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("switch.living_room")
    assert state.state == "off"


async def test_switch_turn_on_calls_api(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test turning the switch on calls the API."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    mock_api.send_command_signal = AsyncMock(return_value={})

    await hass.services.async_call(
        "switch",
        "turn_on",
        {ATTR_ENTITY_ID: "switch.living_room"},
        blocking=True,
    )

    mock_api.send_command_signal.assert_awaited_once_with("sig-on")

    state = hass.states.get("switch.living_room")
    assert state.state == "on"


async def test_switch_turn_off_calls_api(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test turning the switch off calls the API."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    mock_api.send_command_signal = AsyncMock(return_value={})

    await hass.services.async_call(
        "switch",
        "turn_off",
        {ATTR_ENTITY_ID: "switch.living_room"},
        blocking=True,
    )

    mock_api.send_command_signal.assert_awaited_once_with("sig-off")

    state = hass.states.get("switch.living_room")
    assert state.state == "off"


async def test_switch_turn_on_without_power_command_raises(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test turn_on raises when no on command is available."""
    new_appliances = [dict(a) for a in coordinator_data["appliances"]]
    for app in new_appliances:
        if app["id"] == "remote-1":
            app["signals"] = [{"id": "sig-off", "name": "off"}]

    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=new_appliances,
    )

    with pytest.raises(HomeAssistantError, match="Power ON command not available"):
        await hass.services.async_call(
            "switch",
            "turn_on",
            {ATTR_ENTITY_ID: "switch.living_room"},
            blocking=True,
        )


async def test_switch_turn_on_rolls_back_on_api_error(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that state rolls back on API error."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    mock_api.send_command_signal = AsyncMock(side_effect=ClientError("boom"))

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "switch",
            "turn_on",
            {ATTR_ENTITY_ID: "switch.living_room"},
            blocking=True,
        )

    state = hass.states.get("switch.living_room")
    assert state.state == "off"


async def test_switch_turn_on_propagates_auth_error(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test turn_on propagates NatureRemoAuthError as ConfigEntryAuthFailed."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    mock_api.send_command_signal = AsyncMock(
        side_effect=NatureRemoAuthError("unauthorized")
    )

    with pytest.raises(HomeAssistantError, match="Authentication failed"):
        await hass.services.async_call(
            "switch",
            "turn_on",
            {ATTR_ENTITY_ID: "switch.living_room"},
            blocking=True,
        )

    state = hass.states.get("switch.living_room")
    assert state.state == "off"
