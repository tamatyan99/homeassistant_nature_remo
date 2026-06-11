"""Tests for the Nature Remo binary_sensor platform."""

from unittest.mock import AsyncMock

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


async def test_binary_sensor_async_setup_entry_creates_entity(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that async_setup_entry creates the motion binary sensor."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    state = hass.states.get("binary_sensor.bedroom_sensor_motion")
    assert state is not None


async def test_binary_sensor_entity_properties(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test binary sensor entity properties."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    entity_reg = er.async_get(hass)
    entity = entity_reg.async_get("binary_sensor.bedroom_sensor_motion")
    assert entity is not None
    assert entity.unique_id == "nature_remo_dev-2_motion"

    state = hass.states.get("binary_sensor.bedroom_sensor_motion")
    assert state.state == "on"
    assert state.attributes["device_class"] == BinarySensorDeviceClass.MOTION


async def test_binary_sensor_coordinator_update_changes_state(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that coordinator update changes motion state."""
    entry = await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    old_motion = now - timedelta(minutes=10)
    old_motion_str = old_motion.strftime("%Y-%m-%dT%H:%M:%SZ")

    new_devices = [dict(d) for d in coordinator_data["devices"]]
    for dev in new_devices:
        if dev["id"] == "dev-2":
            dev["newest_events"]["mo"]["created_at"] = old_motion_str

    mock_api.get_devices = AsyncMock(return_value=new_devices)
    mock_api.get_appliances = AsyncMock(return_value=coordinator_data["appliances"])

    await hass.data["nature_remo"][entry.entry_id]["coordinator"].async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.bedroom_sensor_motion")
    assert state.state == "off"


async def test_binary_sensor_unavailable_when_sensor_removed(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test sensor becomes unavailable when removed from coordinator."""
    entry = await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    new_devices = [dict(d) for d in coordinator_data["devices"]]
    for dev in new_devices:
        if dev["id"] == "dev-2":
            dev["newest_events"] = {}

    mock_api.get_devices = AsyncMock(return_value=new_devices)
    mock_api.get_appliances = AsyncMock(return_value=coordinator_data["appliances"])

    await hass.data["nature_remo"][entry.entry_id]["coordinator"].async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.bedroom_sensor_motion")
    assert state.state == "unavailable"
