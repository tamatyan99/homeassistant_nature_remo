"""Tests for the Nature Remo climate platform."""

from unittest.mock import AsyncMock

import pytest
from aiohttp import ClientError
from homeassistant.components.climate import (
    PRESET_NONE,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
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
    assert ClimateEntityFeature.SWING_HORIZONTAL_MODE in state.attributes["supported_features"]
    assert ClimateEntityFeature.PRESET_MODE in state.attributes["supported_features"]
    assert state.attributes["swing_horizontal_mode"] == "auto"


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
    """Test turning climate off via climate.turn_off calls the API."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    mock_api.send_command_climate = AsyncMock(return_value={"button": "power-off"})

    await hass.services.async_call(
        "climate",
        "turn_off",
        {ATTR_ENTITY_ID: "climate.living_room"},
        blocking=True,
    )

    mock_api.send_command_climate.assert_awaited_once()
    call_args = mock_api.send_command_climate.await_args
    assert call_args.args[0] == {
        "button": "power-off",
        "temperature_unit": "c",
    }

    state = hass.states.get("climate.living_room")
    assert state.state == HVACMode.OFF


async def test_climate_turn_on_calls_api(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test turning climate on calls the API and defaults to COOL."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    # First turn the unit off
    mock_api.send_command_climate = AsyncMock(return_value={"button": "power-off"})
    await hass.services.async_call(
        "climate",
        "turn_off",
        {ATTR_ENTITY_ID: "climate.living_room"},
        blocking=True,
    )

    mock_api.send_command_climate = AsyncMock(
        return_value={
            "mode": "cool",
            "temp": "25",
            "vol": "auto",
            "dir": "auto",
            "button": "",
        }
    )

    await hass.services.async_call(
        "climate",
        "turn_on",
        {ATTR_ENTITY_ID: "climate.living_room"},
        blocking=True,
    )

    mock_api.send_command_climate.assert_awaited_once()
    call_args = mock_api.send_command_climate.await_args
    assert call_args.args[0] == {
        "operation_mode": "cool",
        "temperature": "25",
        "temperature_unit": "c",
    }
    assert call_args.args[1] == "ac-1"

    state = hass.states.get("climate.living_room")
    assert state.state == HVACMode.COOL


async def test_climate_set_swing_mode_calls_api(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test setting swing mode calls the API."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    mock_api.send_command_climate = AsyncMock(
        return_value={
            "mode": "cool",
            "temp": "25",
            "vol": "auto",
            "dir": "auto",
            "button": "",
        }
    )

    await hass.services.async_call(
        "climate",
        "set_swing_mode",
        {ATTR_ENTITY_ID: "climate.living_room", "swing_mode": "auto"},
        blocking=True,
    )

    mock_api.send_command_climate.assert_awaited_once()
    call_args = mock_api.send_command_climate.await_args
    assert call_args.args[0] == {
        "operation_mode": "cool",
        "air_direction": "auto",
        "temperature_unit": "c",
    }
    assert call_args.args[1] == "ac-1"

    state = hass.states.get("climate.living_room")
    assert state.attributes["swing_mode"] == "auto"


async def test_climate_external_temperature_sensor_override(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that an external temperature sensor overrides the device value."""
    entry = await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
        options={"external_temperature_dev-1": "sensor.outside_temp"},
    )

    hass.states.async_set("sensor.outside_temp", "19.5")

    mock_api.get_devices = AsyncMock(return_value=coordinator_data["devices"])
    mock_api.get_appliances = AsyncMock(return_value=coordinator_data["appliances"])

    await hass.data["nature_remo"][entry.entry_id]["coordinator"].async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("climate.living_room")
    assert state.attributes["current_temperature"] == 19.5


async def test_climate_external_temperature_sensor_fallback_when_unavailable(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test fallback to device events when external temperature sensor is unavailable."""
    entry = await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
        options={"external_temperature_dev-1": "sensor.outside_temp"},
    )

    hass.states.async_set("sensor.outside_temp", "unavailable")

    mock_api.get_devices = AsyncMock(return_value=coordinator_data["devices"])
    mock_api.get_appliances = AsyncMock(return_value=coordinator_data["appliances"])

    await hass.data["nature_remo"][entry.entry_id]["coordinator"].async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("climate.living_room")
    assert state.attributes["current_temperature"] == 22.5


async def test_climate_coordinator_update_refreshes_preset_mode_eco(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that coordinator update refreshes preset mode when button is eco."""
    entry = await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    new_appliances = [dict(a) for a in coordinator_data["appliances"]]
    for app in new_appliances:
        if app["id"] == "ac-1":
            app["settings"] = {
                "mode": "cool",
                "temp": "26.0",
                "vol": "auto",
                "dir": "auto",
                "button": "eco",
            }

    mock_api.get_devices = AsyncMock(return_value=coordinator_data["devices"])
    mock_api.get_appliances = AsyncMock(return_value=new_appliances)

    await hass.data["nature_remo"][entry.entry_id]["coordinator"].async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("climate.living_room")
    assert state.attributes["preset_mode"] == "eco"


async def test_climate_coordinator_update_refreshes_preset_mode_none(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that coordinator update resets preset mode when button is not eco."""
    entry = await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    entity = hass.states.get("climate.living_room")
    assert entity.attributes["preset_mode"] == PRESET_NONE

    new_appliances = [dict(a) for a in coordinator_data["appliances"]]
    for app in new_appliances:
        if app["id"] == "ac-1":
            app["settings"] = {
                "mode": "cool",
                "temp": "26.0",
                "vol": "auto",
                "dir": "auto",
                "button": "eco",
            }

    mock_api.get_devices = AsyncMock(return_value=coordinator_data["devices"])
    mock_api.get_appliances = AsyncMock(return_value=new_appliances)

    await hass.data["nature_remo"][entry.entry_id]["coordinator"].async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("climate.living_room")
    assert state.attributes["preset_mode"] == "eco"

    # Now switch back to non-eco
    for app in new_appliances:
        if app["id"] == "ac-1":
            app["settings"]["button"] = ""

    mock_api.get_appliances = AsyncMock(return_value=new_appliances)

    await hass.data["nature_remo"][entry.entry_id]["coordinator"].async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("climate.living_room")
    assert state.attributes["preset_mode"] == PRESET_NONE


async def test_climate_set_preset_mode_rejects_invalid_preset(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that invalid preset mode is rejected without changing state."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "climate",
            "set_preset_mode",
            {ATTR_ENTITY_ID: "climate.living_room", "preset_mode": "invalid"},
            blocking=True,
        )

    state = hass.states.get("climate.living_room")
    assert state.attributes["preset_mode"] == PRESET_NONE


async def test_climate_set_preset_mode_raises_auth_error(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test auth error is propagated from set_preset_mode."""
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
            "set_preset_mode",
            {ATTR_ENTITY_ID: "climate.living_room", "preset_mode": "eco"},
            blocking=True,
        )


async def test_climate_set_swing_mode_raises_auth_error(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test auth error is propagated from set_swing_mode."""
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
            "set_swing_mode",
            {ATTR_ENTITY_ID: "climate.living_room", "swing_mode": "auto"},
            blocking=True,
        )


async def test_climate_set_swing_horizontal_mode_calls_api(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test setting swing horizontal mode calls the API."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    mock_api.send_command_climate = AsyncMock(
        return_value={
            "mode": "cool",
            "temp": "25",
            "vol": "auto",
            "dir": "auto",
            "dirh": "left",
            "button": "",
        }
    )

    await hass.services.async_call(
        "climate",
        "set_swing_horizontal_mode",
        {ATTR_ENTITY_ID: "climate.living_room", "swing_horizontal_mode": "left"},
        blocking=True,
    )

    mock_api.send_command_climate.assert_awaited_once()
    call_args = mock_api.send_command_climate.await_args
    assert call_args.args[0] == {
        "operation_mode": "cool",
        "air_direction_h": "left",
        "temperature_unit": "c",
    }
    assert call_args.args[1] == "ac-1"

    state = hass.states.get("climate.living_room")
    assert state.attributes["swing_horizontal_mode"] == "left"


async def test_climate_set_swing_horizontal_mode_raises_auth_error(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test auth error is propagated from set_swing_horizontal_mode."""
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
            "set_swing_horizontal_mode",
            {ATTR_ENTITY_ID: "climate.living_room", "swing_horizontal_mode": "left"},
            blocking=True,
        )


async def test_climate_fan_only_temperature_returns_none(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that FAN_ONLY mode with '-' temp returns None target temperature."""
    new_appliances = [dict(a) for a in coordinator_data["appliances"]]
    for app in new_appliances:
        if app["id"] == "ac-1":
            app["settings"] = {
                "mode": "blow",
                "temp": "-",
                "vol": "auto",
                "dir": "auto",
                "button": "",
            }

    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=new_appliances,
    )

    state = hass.states.get("climate.living_room")
    assert state.state == HVACMode.FAN_ONLY
    assert state.attributes["temperature"] is None


async def test_climate_update_from_response_invalid_temp_logs_warning(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api, caplog
):
    """Test that _update_from_response logs a warning for invalid temp."""
    from homeassistant.helpers import entity_platform as ep

    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    climate_platform = None
    for platform in ep.async_get_platforms(hass, "nature_remo"):
        if platform.domain == "climate":
            climate_platform = platform
            break

    assert climate_platform is not None
    entity = list(climate_platform.entities.values())[0]

    import logging

    with caplog.at_level(logging.WARNING):
        entity._update_from_response(
            {"mode": "cool", "temp": "invalid", "button": ""}
        )

    assert "Failed to parse temperature from response" in caplog.text
    assert entity._target_temperature is None


async def test_climate_turn_on_fallback_when_cool_unavailable(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test turn_on falls back to first available mode when COOL is unavailable."""
    new_appliances = [dict(a) for a in coordinator_data["appliances"]]
    for app in new_appliances:
        if app["id"] == "ac-1":
            app["aircon"]["range"]["modes"] = {
                "warm": {
                    "temp": ["18", "25", "30"],
                    "vol": ["1", "2", "3", "auto"],
                    "dir": ["auto"],
                    "dirh": ["auto", "left"],
                }
            }
            app["settings"] = {
                "mode": "warm",
                "temp": "25.0",
                "vol": "auto",
                "dir": "auto",
                "button": "power-off",
            }

    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=new_appliances,
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
        "turn_on",
        {ATTR_ENTITY_ID: "climate.living_room"},
        blocking=True,
    )

    mock_api.send_command_climate.assert_awaited_once()
    call_args = mock_api.send_command_climate.await_args
    assert call_args.args[0] == {
        "operation_mode": "warm",
        "temperature": "25",
        "temperature_unit": "c",
    }

    state = hass.states.get("climate.living_room")
    assert state.state == HVACMode.HEAT
