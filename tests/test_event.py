"""Tests for the Nature Remo event platform."""

from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


async def test_event_async_setup_entry_creates_entity(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that async_setup_entry creates the motion event entity."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    state = hass.states.get("event.bedroom_sensor_motion_event")
    assert state is not None


async def test_event_entity_properties(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test event entity properties."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    entity_reg = er.async_get(hass)
    entity = entity_reg.async_get("event.bedroom_sensor_motion_event")
    assert entity is not None
    assert entity.unique_id == "nature_remo_dev-2_motion_event"

    state = hass.states.get("event.bedroom_sensor_motion_event")
    assert state.attributes["event_types"] == ["motion_detected"]


async def test_event_fires_on_motion_update(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that event fires when motion timestamp changes."""
    entry = await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    new_time = now - timedelta(seconds=30)
    new_time_str = new_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    new_devices = [dict(d) for d in coordinator_data["devices"]]
    for dev in new_devices:
        if dev["id"] == "dev-2":
            dev["newest_events"]["mo"]["created_at"] = new_time_str

    mock_api.get_devices = AsyncMock(return_value=new_devices)
    mock_api.get_appliances = AsyncMock(return_value=coordinator_data["appliances"])

    await hass.data["nature_remo"][entry.entry_id]["coordinator"].async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("event.bedroom_sensor_motion_event")
    assert state.attributes["event_type"] == "motion_detected"
    assert "device_id" in state.attributes
    assert "last_motion" in state.attributes


async def test_event_does_not_fire_on_same_timestamp(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test event does not fire when timestamp is unchanged."""
    entry = await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    # First refresh with same data
    mock_api.get_devices = AsyncMock(return_value=coordinator_data["devices"])
    mock_api.get_appliances = AsyncMock(return_value=coordinator_data["appliances"])

    await hass.data["nature_remo"][entry.entry_id]["coordinator"].async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("event.bedroom_sensor_motion_event")
    assert state.attributes.get("event_type") is None


