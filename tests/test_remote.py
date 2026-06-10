"""Tests for the Nature Remo remote platform."""

from unittest.mock import AsyncMock

import pytest
from aiohttp import ClientError
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er


async def test_remote_async_setup_entry_creates_entity(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that async_setup_entry creates the remote entity."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    state = hass.states.get("remote.living_room")
    assert state is not None


async def test_remote_entity_properties(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test remote entity properties."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    entity_reg = er.async_get(hass)
    entity = entity_reg.async_get("remote.living_room")
    assert entity is not None
    assert entity.unique_id == "nature_remo_remote_remote-1"

    state = hass.states.get("remote.living_room")
    assert state.attributes["available_commands"] == ["on", "off", "volume up"]
    assert "command" in state.attributes


async def test_remote_coordinator_update_changes_commands(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that coordinator update refreshes available commands."""
    entry = await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    state = hass.states.get("remote.living_room")
    assert state.attributes["available_commands"] == ["on", "off", "volume up"]

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

    state = hass.states.get("remote.living_room")
    assert state.attributes["available_commands"] == ["on", "off", "input"]


async def test_remote_send_command_calls_api(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test sending a command calls the API."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    mock_api.send_command_signal = AsyncMock(return_value={})

    await hass.services.async_call(
        "remote",
        "send_command",
        {ATTR_ENTITY_ID: "remote.living_room", "command": ["volume up"]},
        blocking=True,
    )

    mock_api.send_command_signal.assert_awaited_once_with("sig-vol-up")


async def test_remote_turn_on_calls_api(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test turning the remote on calls the API."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    mock_api.send_command_signal = AsyncMock(return_value={})

    await hass.services.async_call(
        "remote",
        "turn_on",
        {ATTR_ENTITY_ID: "remote.living_room"},
        blocking=True,
    )

    mock_api.send_command_signal.assert_awaited_once_with("sig-on")

    state = hass.states.get("remote.living_room")
    assert state.attributes["command"] == "on"


async def test_remote_turn_off_calls_api(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test turning the remote off calls the API."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    mock_api.send_command_signal = AsyncMock(return_value={})

    await hass.services.async_call(
        "remote",
        "turn_off",
        {ATTR_ENTITY_ID: "remote.living_room"},
        blocking=True,
    )

    mock_api.send_command_signal.assert_awaited_once_with("sig-off")

    state = hass.states.get("remote.living_room")
    assert state.attributes["command"] == "off"


async def test_remote_turn_on_without_power_command_raises(
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
            "remote",
            "turn_on",
            {ATTR_ENTITY_ID: "remote.living_room"},
            blocking=True,
        )


async def test_remote_send_command_failure_raises_error(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test failed send_command raises ServiceValidationError."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    mock_api.send_command_signal = AsyncMock(side_effect=ClientError("boom"))

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "remote",
            "send_command",
            {ATTR_ENTITY_ID: "remote.living_room", "command": ["volume up"]},
            blocking=True,
        )
