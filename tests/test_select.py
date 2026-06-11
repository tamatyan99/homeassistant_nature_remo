"""Tests for the Nature Remo select platform."""

from unittest.mock import AsyncMock

import pytest
from aiohttp import ClientError
from homeassistant.const import ATTR_ENTITY_ID, ATTR_OPTION
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er


async def test_select_async_setup_entry_creates_entities(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that async_setup_entry creates the select entities."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    assert hass.states.get("select.living_room_mode") is not None
    assert hass.states.get("select.living_room_preset") is not None


async def test_select_light_mode_entity_properties(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test light mode select entity properties."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    entity_reg = er.async_get(hass)
    entity = entity_reg.async_get("select.living_room_mode")
    assert entity is not None
    assert entity.unique_id == "nature_remo_light_select_light-1"

    state = hass.states.get("select.living_room_mode")
    assert state.attributes["options"] == ["on", "off", "night"]


async def test_select_ac_preset_entity_properties(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test AC preset select entity properties."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    entity_reg = er.async_get(hass)
    entity = entity_reg.async_get("select.living_room_preset")
    assert entity is not None
    assert entity.unique_id == "nature_remo_ac_preset_ac-1"

    state = hass.states.get("select.living_room_preset")
    assert state.attributes["options"] == ["none", "eco"]


async def test_select_light_mode_coordinator_update_changes_options(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that coordinator update changes light mode options and current."""
    entry = await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    new_appliances = [dict(a) for a in coordinator_data["appliances"]]
    for app in new_appliances:
        if app["id"] == "light-1":
            app["light"]["state"]["last_button"] = "night"
            app["light"]["buttons"] = [
                {"name": "on"},
                {"name": "off"},
                {"name": "night"},
                {"name": "reading"},
            ]

    mock_api.get_devices = AsyncMock(return_value=coordinator_data["devices"])
    mock_api.get_appliances = AsyncMock(return_value=new_appliances)

    await hass.data["nature_remo"][entry.entry_id]["coordinator"].async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("select.living_room_mode")
    assert state.attributes["options"] == ["on", "off", "night", "reading"]
    assert state.state == "night"


async def test_select_light_mode_select_option_calls_api(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test selecting a light mode option calls the API."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    mock_api.send_light_command = AsyncMock(return_value={})

    await hass.services.async_call(
        "select",
        "select_option",
        {ATTR_ENTITY_ID: "select.living_room_mode", ATTR_OPTION: "night"},
        blocking=True,
    )

    mock_api.send_light_command.assert_awaited_once_with("light-1", "night")

    state = hass.states.get("select.living_room_mode")
    assert state.state == "night"


async def test_select_ac_preset_eco_calls_api(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test selecting eco preset calls the API."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    mock_api.send_command_climate = AsyncMock(
        return_value={"button": "eco", "temp": "26"}
    )

    await hass.services.async_call(
        "select",
        "select_option",
        {ATTR_ENTITY_ID: "select.living_room_preset", ATTR_OPTION: "eco"},
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


async def test_select_light_mode_invalid_option_raises(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test selecting an invalid option raises an error."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    with pytest.raises(HomeAssistantError, match="not valid for entity"):
        await hass.services.async_call(
            "select",
            "select_option",
            {ATTR_ENTITY_ID: "select.living_room_mode", ATTR_OPTION: "disco"},
            blocking=True,
        )


async def test_select_light_mode_rolls_back_on_api_error(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that light mode rolls back on API error."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    mock_api.send_light_command = AsyncMock(side_effect=ClientError("boom"))

    with pytest.raises(HomeAssistantError, match="Command failed"):
        await hass.services.async_call(
            "select",
            "select_option",
            {ATTR_ENTITY_ID: "select.living_room_mode", ATTR_OPTION: "night"},
            blocking=True,
        )

    state = hass.states.get("select.living_room_mode")
    # Current option may be None initially from coordinator data
    assert state.state in ("unknown", "on")


async def test_select_light_mode_handles_null_light(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that light mode select handles null light data from API."""
    new_appliances = [dict(a) for a in coordinator_data["appliances"]]
    for app in new_appliances:
        if app["id"] == "light-1":
            app["light"] = None

    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=new_appliances,
    )

    state = hass.states.get("select.living_room_mode")
    assert state is not None
    assert state.attributes["options"] == []


async def test_select_ac_preset_handles_null_settings(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that AC preset select handles null settings data from API."""
    new_appliances = [dict(a) for a in coordinator_data["appliances"]]
    for app in new_appliances:
        if app["id"] == "ac-1":
            app["settings"] = None

    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=new_appliances,
    )

    state = hass.states.get("select.living_room_preset")
    assert state is not None
    assert state.state == "none"


async def test_select_ac_preset_none_with_null_settings_is_noop(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that selecting none with null AC settings does not crash."""
    new_appliances = [dict(a) for a in coordinator_data["appliances"]]
    for app in new_appliances:
        if app["id"] == "ac-1":
            app["settings"] = None

    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=new_appliances,
    )

    mock_api.send_command_climate = AsyncMock(return_value={})

    await hass.services.async_call(
        "select",
        "select_option",
        {ATTR_ENTITY_ID: "select.living_room_preset", ATTR_OPTION: "none"},
        blocking=True,
    )

    mock_api.send_command_climate.assert_not_awaited()
    state = hass.states.get("select.living_room_preset")
    assert state.state == "none"


async def test_select_light_mode_clears_state_when_appliance_removed(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that light mode select clears options when appliance disappears."""
    entry = await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    new_appliances = [a for a in coordinator_data["appliances"] if a["id"] != "light-1"]

    mock_api.get_devices = AsyncMock(return_value=coordinator_data["devices"])
    mock_api.get_appliances = AsyncMock(return_value=new_appliances)

    await hass.data["nature_remo"][entry.entry_id]["coordinator"].async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("select.living_room_mode")
    assert state.attributes["options"] == []
    assert state.state == "unknown"


async def test_select_ac_preset_clears_state_when_appliance_removed(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that AC preset select resets to none when appliance disappears."""
    entry = await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    new_appliances = [a for a in coordinator_data["appliances"] if a["id"] != "ac-1"]

    mock_api.get_devices = AsyncMock(return_value=coordinator_data["devices"])
    mock_api.get_appliances = AsyncMock(return_value=new_appliances)

    await hass.data["nature_remo"][entry.entry_id]["coordinator"].async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("select.living_room_preset")
    assert state.state == "none"
