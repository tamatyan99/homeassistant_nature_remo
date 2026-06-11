"""Tests for the Nature Remo button platform."""

from unittest.mock import AsyncMock

import pytest
from aiohttp import ClientError
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er


async def test_button_async_setup_entry_creates_entities(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that async_setup_entry creates the button entities."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    assert hass.states.get("button.living_room_learn_signal") is not None
    assert hass.states.get("button.living_room_refresh_data") is not None
    assert hass.states.get("button.bedroom_sensor_refresh_data") is not None


async def test_button_learn_signal_entity_properties(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test learn signal button properties."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    entity_reg = er.async_get(hass)
    entity = entity_reg.async_get("button.living_room_learn_signal")
    assert entity is not None
    assert entity.unique_id == "nature_remo_learn_signal_remote-1"

    state = hass.states.get("button.living_room_learn_signal")
    assert state.attributes["icon"] == "mdi:remote"


async def test_button_refresh_data_entity_properties(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test refresh data button properties."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    entity_reg = er.async_get(hass)
    entity = entity_reg.async_get("button.living_room_refresh_data")
    assert entity is not None
    assert entity.unique_id == "nature_remo_refresh_dev-1"

    state = hass.states.get("button.living_room_refresh_data")
    assert state.attributes["icon"] == "mdi:refresh"


async def test_button_learn_signal_press_calls_api(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test pressing learn signal button calls the API."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    mock_api.learn_signal = AsyncMock(return_value={"id": "new-signal"})

    await hass.services.async_call(
        "button",
        "press",
        {ATTR_ENTITY_ID: "button.living_room_learn_signal"},
        blocking=True,
    )

    mock_api.learn_signal.assert_awaited_once_with("remote-1")


async def test_button_refresh_data_press_calls_coordinator(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test pressing refresh data button requests coordinator refresh."""
    entry = await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    coordinator = hass.data["nature_remo"][entry.entry_id]["coordinator"]
    coordinator.async_request_refresh = AsyncMock()

    await hass.services.async_call(
        "button",
        "press",
        {ATTR_ENTITY_ID: "button.living_room_refresh_data"},
        blocking=True,
    )

    coordinator.async_request_refresh.assert_awaited_once()


async def test_button_learn_signal_press_raises_on_api_error(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test API error during learn signal press raises HomeAssistantError."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    mock_api.learn_signal = AsyncMock(side_effect=ClientError("boom"))

    with pytest.raises(HomeAssistantError, match="Learn signal failed"):
        await hass.services.async_call(
            "button",
            "press",
            {ATTR_ENTITY_ID: "button.living_room_learn_signal"},
            blocking=True,
        )
