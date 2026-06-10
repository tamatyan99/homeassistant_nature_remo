"""Tests for the Nature Remo climate platform."""

from unittest.mock import AsyncMock

import pytest
from aiohttp import ClientError
from homeassistant.components.climate import (
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import entity_registry as er

from custom_components.nature_remo.api import NatureRemoAuthError


async def test_climate_async_setup_entry_creates_entity(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that async_setup_entry creates the climate entity."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    state = hass.states.get("climate.living_room")
    assert state is not None
    assert state.state == HVACMode.COOL


async def test_climate_entity_properties(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test climate entity properties."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    entity_reg = er.async_get(hass)
    entity = entity_reg.async_get("climate.living_room")
    assert entity is not None
    assert entity.unique_id == "nature_remo_climate_ac-1"

    state = hass.states.get("climate.living_room")
    assert state.attributes["friendly_name"] == "Living Room"
    assert HVACMode.OFF in state.attributes["hvac_modes"]
    assert HVACMode.COOL in state.attributes["hvac_modes"]
    assert ClimateEntityFeature.TARGET_TEMPERATURE in state.attributes["supported_features"]
    assert ClimateEntityFeature.FAN_MODE in state.attributes["supported_features"]
    assert ClimateEntityFeature.SWING_MODE in state.attributes["supported_features"]
    assert ClimateEntityFeature.PRESET_MODE in state.attributes["supported_features"]


async def test_climate_coordinator_update_changes_state(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that coordinator update changes the entity state."""
    entry = await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    state = hass.states.get("climate.living_room")
    assert state.state == HVACMode.COOL

    new_appliances = [dict(a) for a in coordinator_data["appliances"]]
    for app in new_appliances:
        if app["id"] == "ac-1":
            app["settings"] = {
                "mode": "warm",
                "temp": "27.0",
                "vol": "2",
                "dir": "auto",
                "button": "",
            }

    mock_api.get_devices = AsyncMock(return_value=coordinator_data["devices"])
    mock_api.get_appliances = AsyncMock(return_value=new_appliances)

    await hass.data["nature_remo"][entry.entry_id]["coordinator"].async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("climate.living_room")
    assert state.state == HVACMode.HEAT
    assert state.attributes["temperature"] == 27.0
    assert state.attributes["fan_mode"] == "2"


async def test_climate_set_hvac_mode_calls_api(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test setting HVAC mode calls the API."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    mock_api.send_command_climate = AsyncMock(
        return_value={
            "mode": "warm",
            "temp": "25",
            "vol": "auto",
            "dir": "auto",
            "button": "",
        }
    )

    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {ATTR_ENTITY_ID: "climate.living_room", "hvac_mode": "heat"},
        blocking=True,
    )

    mock_api.send_command_climate.assert_awaited_once()
    call_args = mock_api.send_command_climate.await_args
    assert call_args.args[0] == {
        "operation_mode": "warm",
        "temperature": "25",
        "temperature_unit": "c",
    }
    assert call_args.args[1] == "ac-1"

    state = hass.states.get("climate.living_room")
    assert state.state == HVACMode.HEAT


async def test_climate_set_temperature_calls_api(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test setting temperature calls the API."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    mock_api.send_command_climate = AsyncMock(
        return_value={
            "mode": "cool",
            "temp": "22",
            "vol": "auto",
            "dir": "auto",
            "button": "",
        }
    )

    await hass.services.async_call(
        "climate",
        "set_temperature",
        {ATTR_ENTITY_ID: "climate.living_room", "temperature": 22.0},
        blocking=True,
    )

    mock_api.send_command_climate.assert_awaited_once()
    call_args = mock_api.send_command_climate.await_args
    assert call_args.args[0] == {
        "operation_mode": "cool",
        "temperature": "22",
        "temperature_unit": "c",
    }
    assert call_args.args[1] == "ac-1"


async def test_climate_set_preset_mode_eco_calls_api(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test setting eco preset mode calls the API."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    mock_api.send_command_climate = AsyncMock(
        return_value={
            "mode": "cool",
            "temp": "26",
            "vol": "auto",
            "dir": "auto",
            "button": "eco",
        }
    )

    await hass.services.async_call(
        "climate",
        "set_preset_mode",
        {ATTR_ENTITY_ID: "climate.living_room", "preset_mode": "eco"},
        blocking=True,
    )

    mock_api.send_command_climate.assert_awaited_once()
    call_args = mock_api.send_command_climate.await_args
    assert call_args.args[0] == {
        "button": "eco",
        "temperature": "26",
        "temperature_unit": "c",
    }
    assert call_args.args[1] == "ac-1"


async def test_climate_set_fan_mode_calls_api(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test setting fan mode calls the API."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    mock_api.send_command_climate = AsyncMock(
        return_value={
            "mode": "cool",
            "temp": "25",
            "vol": "2",
            "dir": "auto",
            "button": "",
        }
    )

    await hass.services.async_call(
        "climate",
        "set_fan_mode",
        {ATTR_ENTITY_ID: "climate.living_room", "fan_mode": "2"},
        blocking=True,
    )

    mock_api.send_command_climate.assert_awaited_once()
    call_args = mock_api.send_command_climate.await_args
    assert call_args.args[0] == {
        "operation_mode": "cool",
        "air_volume": "2",
        "temperature_unit": "c",
    }
    assert call_args.args[1] == "ac-1"


async def test_climate_set_hvac_mode_rolls_back_on_api_error(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that state rolls back on API error."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    mock_api.send_command_climate = AsyncMock(side_effect=ClientError("boom"))

    with pytest.raises(ClientError):
        await hass.services.async_call(
            "climate",
            "set_hvac_mode",
            {ATTR_ENTITY_ID: "climate.living_room", "hvac_mode": "heat"},
            blocking=True,
        )

    state = hass.states.get("climate.living_room")
    assert state.state == HVACMode.COOL


async def test_climate_set_hvac_mode_raises_auth_error(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test auth error is propagated."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    mock_api.send_command_climate = AsyncMock(
        side_effect=NatureRemoAuthError("401")
    )

    with pytest.raises(ConfigEntryAuthFailed):
        await hass.services.async_call(
            "climate",
            "set_hvac_mode",
            {ATTR_ENTITY_ID: "climate.living_room", "hvac_mode": "heat"},
            blocking=True,
        )


async def test_climate_turn_off_calls_api(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test turning climate off calls the API."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    mock_api.send_command_climate = AsyncMock(return_value={"button": "power-off"})

    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {ATTR_ENTITY_ID: "climate.living_room", "hvac_mode": "off"},
        blocking=True,
    )

    mock_api.send_command_climate.assert_awaited_once()
    call_args = mock_api.send_command_climate.await_args
    assert call_args.args[0] == {"button": "power-off"}

    state = hass.states.get("climate.living_room")
    assert state.state == HVACMode.OFF
