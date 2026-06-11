"""Tests for the Nature Remo light platform."""

from unittest.mock import AsyncMock

import pytest
from aiohttp import ClientError
from homeassistant.components.light import ColorMode, LightEntityFeature
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers import entity_registry as er

from custom_components.nature_remo.api import NatureRemoAuthError


async def test_light_async_setup_entry_creates_entity(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that async_setup_entry creates the light entity."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    state = hass.states.get("light.living_room")
    assert state is not None
    assert state.state == "on"


async def test_light_entity_properties(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test light entity properties."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    entity_reg = er.async_get(hass)
    entity = entity_reg.async_get("light.living_room")
    assert entity is not None
    assert entity.unique_id == "nature_remo_light_light-1"

    state = hass.states.get("light.living_room")
    assert state.attributes["friendly_name"] == "Living Room"
    assert ColorMode.ONOFF in state.attributes["supported_color_modes"]
    assert LightEntityFeature.EFFECT in state.attributes["supported_features"]
    assert state.attributes["effect_list"] == ["on", "off", "night"]
    assert state.attributes["remo_light_mode"] == "on"
    assert state.attributes["effect"] == "on"


async def test_light_effect_property_when_off(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test light effect property returns None when off."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    await hass.services.async_call(
        "light",
        "turn_off",
        {ATTR_ENTITY_ID: "light.living_room"},
        blocking=True,
    )

    state = hass.states.get("light.living_room")
    assert state.state == "off"
    assert state.attributes["effect"] is None


async def test_light_coordinator_update_changes_state(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that coordinator update changes the entity state."""
    entry = await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    state = hass.states.get("light.living_room")
    assert state.state == "on"

    new_appliances = [dict(a) for a in coordinator_data["appliances"]]
    for app in new_appliances:
        if app["id"] == "light-1":
            app["light"]["state"] = {"power": "off", "last_button": "off"}

    mock_api.get_devices = AsyncMock(return_value=coordinator_data["devices"])
    mock_api.get_appliances = AsyncMock(return_value=new_appliances)

    await hass.data["nature_remo"][entry.entry_id]["coordinator"].async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("light.living_room")
    assert state.state == "off"
    assert state.attributes["remo_light_mode"] == "off"


async def test_light_turn_on_calls_api(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test turning the light on calls the API."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    mock_api.send_light_command = AsyncMock(return_value={})

    await hass.services.async_call(
        "light",
        "turn_on",
        {ATTR_ENTITY_ID: "light.living_room", "effect": "night"},
        blocking=True,
    )

    mock_api.send_light_command.assert_awaited_once_with("light-1", "night")

    state = hass.states.get("light.living_room")
    assert state.state == "on"
    assert state.attributes["remo_light_mode"] == "night"


async def test_light_turn_off_calls_api(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test turning the light off calls the API."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    mock_api.send_light_command = AsyncMock(return_value={})

    await hass.services.async_call(
        "light",
        "turn_off",
        {ATTR_ENTITY_ID: "light.living_room"},
        blocking=True,
    )

    mock_api.send_light_command.assert_awaited_once_with("light-1", "off")

    state = hass.states.get("light.living_room")
    assert state.state == "off"


async def test_light_unsupported_effect_raises_error(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test unsupported effect raises an error."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    with pytest.raises(HomeAssistantError, match="Effect 'disco' is not supported"):
        await hass.services.async_call(
            "light",
            "turn_on",
            {ATTR_ENTITY_ID: "light.living_room", "effect": "disco"},
            blocking=True,
        )


async def test_light_turn_on_rolls_back_on_api_error(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that state rolls back on API error."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    mock_api.send_light_command = AsyncMock(side_effect=ClientError("boom"))

    with pytest.raises(ClientError):
        await hass.services.async_call(
            "light",
            "turn_on",
            {ATTR_ENTITY_ID: "light.living_room", "effect": "night"},
            blocking=True,
        )

    state = hass.states.get("light.living_room")
    assert state.state == "on"
    assert state.attributes["remo_light_mode"] == "on"


async def test_light_turn_on_raises_auth_error(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test auth error is propagated."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    mock_api.send_light_command = AsyncMock(side_effect=NatureRemoAuthError("401"))

    with pytest.raises(ConfigEntryAuthFailed):
        await hass.services.async_call(
            "light",
            "turn_on",
            {ATTR_ENTITY_ID: "light.living_room"},
            blocking=True,
        )
